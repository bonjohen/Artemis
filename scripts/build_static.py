#!/usr/bin/env python3
"""Static site generator for Artemis Calendar GitHub Pages deployment.

Generates a complete static site from the warehouse database by:
1. Pre-generating all API responses as JSON files
2. Copying the SPA frontend (HTML, CSS, JS)
3. Injecting a fetch shim that redirects API calls to static JSON files
4. Rewriting thumbnail URLs to the R2 CDN

Usage:
    python scripts/build_static.py
    python scripts/build_static.py --output _site --base-path /Artemis

Prerequisites:
    - warehouse.duckdb must be populated
    - pip install .[web]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

# R2 CDN base for thumbnails — avoids shipping 244MB of images in the repo
THUMB_CDN = "https://pub-1f1ce68455c0432ea65ac3155a6b2409.r2.dev/thumbs"

# ---------------------------------------------------------------------------
# Fetch shim — intercepts fetch() and serves from pre-built JSON files.
# Handles pagination, sorting, and filtering client-side.
# ---------------------------------------------------------------------------

STATIC_SHIM = r"""<script>
(function(){
var F=window.fetch,IC=null,DC=null;
function LI(b){if(!IC)IC=F(b+'api/images/all.json').then(function(r){return r.json()});return IC;}
function LD(b){if(!DC)DC=F(b+'api/images/details.json').then(function(r){return r.json()});return DC;}
window.fetch=function(u,opts){
  if(typeof u!=='string')return F.apply(this,arguments);
  var ai=u.indexOf('/api/');
  if(ai<0)return F.apply(this,arguments);
  var b=u.substring(0,ai+1);
  var r=u.substring(ai);
  var qi=r.indexOf('?'),p=qi>=0?r.substring(0,qi):r;
  var sp=new URLSearchParams(qi>=0?r.substring(qi+1):'');
  /* Health */
  if(p==='/api/health'){
    return Promise.resolve(new Response('{"status":"ok"}',{headers:{'Content-Type':'application/json'}}));
  }
  /* Images list — load all, filter/sort/paginate client-side */
  if(p==='/api/images'){
    return LI(b).then(function(all){
      var items=all.slice();
      var cid=sp.get('cluster_id'),ms=sp.get('min_score'),sort=sp.get('sort')||'score';
      if(cid!==null)items=items.filter(function(x){return x.cluster_id===+cid});
      if(ms!==null)items=items.filter(function(x){return (x.preference_score||0)>=+ms});
      if(sort==='score')items.sort(function(a,b){return (b.preference_score||0)-(a.preference_score||0)});
      else if(sort==='brightness')items.sort(function(a,b){return (b.brightness_score||0)-(a.brightness_score||0)});
      else if(sort==='cluster')items.sort(function(a,b){return (a.cluster_id||999)-(b.cluster_id||999)||(b.preference_score||0)-(a.preference_score||0)});
      var pg=+(sp.get('page')||1),pp=+(sp.get('per_page')||60);
      var start=(pg-1)*pp;
      var body={items:items.slice(start,start+pp),total:items.length,page:pg,pages:Math.max(1,Math.ceil(items.length/pp))};
      return new Response(JSON.stringify(body),{headers:{'Content-Type':'application/json'}});
    });
  }
  /* Image detail */
  var im=p.match(/^\/api\/images\/(\d+)$/);
  if(im){
    return LD(b).then(function(d){
      var detail=d[im[1]];
      if(!detail)return new Response('{"detail":"Not found"}',{status:404,headers:{'Content-Type':'application/json'}});
      return new Response(JSON.stringify(detail),{headers:{'Content-Type':'application/json'}});
    });
  }
  /* Clusters list */
  if(p==='/api/clusters'){return F(b+'api/clusters/index.json');}
  /* Cluster detail — load members, paginate client-side */
  var cm=p.match(/^\/api\/clusters\/(\d+)$/);
  if(cm){
    return F(b+'api/clusters/'+cm[1]+'.json').then(function(r){return r.json()}).then(function(all){
      var pg=+(sp.get('page')||1),pp=+(sp.get('per_page')||60);
      var start=(pg-1)*pp;
      var body={items:all.slice(start,start+pp),total:all.length,page:pg,pages:Math.max(1,Math.ceil(all.length/pp))};
      return new Response(JSON.stringify(body),{headers:{'Content-Type':'application/json'}});
    });
  }
  /* Candidates list */
  if(p==='/api/candidates'){return F(b+'api/candidates/index.json');}
  /* Candidate detail */
  var cn=p.match(/^\/api\/candidates\/(.+)$/);
  if(cn){return F(b+'api/candidates/'+cn[1]+'.json');}
  /* Stats */
  if(p==='/api/stats'){return F(b+'api/stats.json');}
  /* Selection — read-only in static mode */
  if(p==='/api/selection'&&(!opts||!opts.method||opts.method==='GET')){
    return Promise.resolve(new Response(JSON.stringify({name:sp.get('name')||'current',assignments:[],notes:'Static site — selection builder is read-only.'}),
      {headers:{'Content-Type':'application/json'}}));
  }
  if(p==='/api/selection'){
    return Promise.resolve(new Response(JSON.stringify({detail:'Selection save is not available on the static site. Run the local server for interactive selection.'}),
      {status:501,headers:{'Content-Type':'application/json'}}));
  }
  if(p==='/api/selection/score'){
    return Promise.resolve(new Response(JSON.stringify({detail:'Scoring requires the local server with CLIP embeddings loaded.'}),
      {status:501,headers:{'Content-Type':'application/json'}}));
  }
  /* Fallback — try .json extension */
  return F(b+p.substring(1)+'.json');
};
})();
</script>"""


def build_static(base_path: str, output_dir: str) -> None:
    from starlette.testclient import TestClient

    from artemis_calendar.web.app import create_app

    output = Path(output_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    bp = base_path.rstrip("/") if base_path != "/" else ""

    # --- Create test client (context manager triggers lifespan/init_db) ---
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    client.__enter__()

    # --- Copy static assets ---
    static_src = _project_root / "src" / "artemis_calendar" / "web" / "static"
    static_dst = output / "static"
    shutil.copytree(static_src, static_dst)

    # Rewrite thumbnail URLs from /thumbs/ to R2 CDN
    for js_file in static_dst.rglob("*.js"):
        content = js_file.read_text(encoding="utf-8")
        rewritten = content.replace("/thumbs/", THUMB_CDN + "/")
        if bp:
            rewritten = rewritten.replace('"/api/', f'"{bp}/api/')
            rewritten = rewritten.replace("'/api/", f"'{bp}/api/")
            rewritten = rewritten.replace("`/api/", f"`{bp}/api/")
            rewritten = rewritten.replace('"/static/', f'"{bp}/static/')
            rewritten = rewritten.replace("'/static/", f"'{bp}/static/")
        if rewritten != content:
            js_file.write_text(rewritten, encoding="utf-8")
    print("  Copied and patched static assets")

    # --- Generate index.html with shim ---
    index_src = static_src / "index.html"
    index_html = index_src.read_text(encoding="utf-8")
    # Rewrite asset paths for base path
    if bp:
        index_html = index_html.replace('"/static/', f'"{bp}/static/')
        index_html = index_html.replace("'/static/", f"'{bp}/static/")
    # Inject fetch shim before </head>
    index_html = index_html.replace("</head>", STATIC_SHIM + "\n</head>")
    (output / "index.html").write_text(index_html, encoding="utf-8")
    print("  Generated index.html with fetch shim")

    # --- Helper ---
    def write_json(url: str, filepath: str) -> bool:
        resp = client.get(url)
        if resp.status_code != 200:
            print(f"    WARN: {url} returned {resp.status_code}")
            return False
        dest = output / filepath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resp.text, encoding="utf-8")
        return True

    # --- API: Stats ---
    print("\nGenerating API data...")
    write_json("/api/stats", "api/stats.json")
    write_json("/api/health", "api/health.json")
    print("  Stats + health")

    # --- API: Images (all summaries for client-side filtering) ---
    t0 = time.time()
    # Fetch all pages to build the complete image list
    all_images: list[dict] = []
    page = 1
    while True:
        resp = client.get(f"/api/images?page={page}&per_page=200&sort=score")
        if resp.status_code != 200:
            break
        data = resp.json()
        all_images.extend(data["items"])
        if page >= data["pages"]:
            break
        page += 1

    images_dir = output / "api" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / "all.json").write_text(json.dumps(all_images), encoding="utf-8")
    elapsed = time.time() - t0
    print(f"  {len(all_images)} image summaries ({elapsed:.1f}s)")

    # --- API: Image details (bundled into one file, keyed by sk) ---
    t0 = time.time()
    all_details: dict[str, dict] = {}
    batch_size = 50
    sks = [img["image_sk"] for img in all_images]
    for i in range(0, len(sks), batch_size):
        batch = sks[i : i + batch_size]
        for sk in batch:
            resp = client.get(f"/api/images/{sk}")
            if resp.status_code == 200:
                all_details[str(sk)] = resp.json()
        done = min(i + batch_size, len(sks))
        if done % 500 == 0 or done == len(sks):
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            remaining = (len(sks) - done) / rate if rate > 0 else 0
            print(f"    {done}/{len(sks)} image details ({rate:.0f}/s, ~{remaining:.0f}s left)")

    (images_dir / "details.json").write_text(json.dumps(all_details), encoding="utf-8")
    elapsed = time.time() - t0
    print(f"  {len(all_details)} image details ({elapsed:.1f}s)")

    # --- API: Candidates ---
    resp = client.get("/api/candidates")
    candidates = resp.json() if resp.status_code == 200 else []
    cand_dir = output / "api" / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    (cand_dir / "index.json").write_text(json.dumps(candidates), encoding="utf-8")

    for cand in candidates:
        name = cand["candidate_name"]
        write_json(f"/api/candidates/{name}", f"api/candidates/{name}.json")
    print(f"  {len(candidates)} candidates")

    # --- API: Clusters ---
    resp = client.get("/api/clusters")
    clusters = resp.json() if resp.status_code == 200 else []
    clust_dir = output / "api" / "clusters"
    clust_dir.mkdir(parents=True, exist_ok=True)
    (clust_dir / "index.json").write_text(json.dumps(clusters), encoding="utf-8")

    for cluster in clusters:
        cid = cluster["cluster_id"]
        # Fetch ALL members (not paginated) for client-side pagination
        all_members: list[dict] = []
        page = 1
        while True:
            resp = client.get(f"/api/clusters/{cid}?page={page}&per_page=200")
            if resp.status_code != 200:
                break
            data = resp.json()
            all_members.extend([item if isinstance(item, dict) else item.dict() for item in data["items"]])
            if page >= data["pages"]:
                break
            page += 1
        (clust_dir / f"{cid}.json").write_text(json.dumps(all_members), encoding="utf-8")
    print(f"  {len(clusters)} clusters")

    # --- GitHub Pages files ---
    (output / ".nojekyll").write_text("", encoding="utf-8")
    # 404 page — redirect to index for SPA
    (output / "404.html").write_text(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={bp or '/'}">
</head><body>Redirecting...</body></html>""",
        encoding="utf-8",
    )
    print("\n  Created .nojekyll + 404.html")

    # --- Cleanup ---
    client.__exit__(None, None, None)

    # --- Summary ---
    total_files = sum(1 for _ in output.rglob("*") if _.is_file())
    total_size_mb = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"\nBuild complete: {total_files} files, {total_size_mb:.1f} MB in {output}")


def main():
    parser = argparse.ArgumentParser(description="Build static site for GitHub Pages")
    parser.add_argument("--output", default="_site", help="Output directory (default: _site)")
    parser.add_argument("--base-path", default="/", help="Base path for GitHub Pages (e.g., /Artemis)")
    args = parser.parse_args()
    build_static(args.base_path, args.output)


if __name__ == "__main__":
    main()
