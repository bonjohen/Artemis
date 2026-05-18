# Lesson 064: Noscript Fallback as SEO Baseline for SPAs

## The Lesson

A single-page application rendered entirely in JavaScript is invisible to search engine crawlers that don't execute JS. Adding a `<noscript>` block with the project's core content — title, summary, key links, and attribution — provides a crawlable baseline that costs minutes to implement and ensures the site exists in search results regardless of the crawler's JS capabilities.

## Context

A data science case study site was built as a vanilla JS SPA with hash-based routing. All page content was rendered client-side by JavaScript modules. The HTML file contained only a `<nav>`, a `<main>` shell, and a `<script>` tag. Search engines that don't execute JavaScript (or that deprioritize JS-rendered content) would see an empty page with a loading spinner.

## What Happened

1. The site was deployed to a custom domain for portfolio use. The goal was for the project to appear in search results when someone searched for the author's name or "Artemis calendar image selection."

2. Added OpenGraph meta tags (`og:title`, `og:description`, `og:type`, `og:url`) to the `<head>` for social sharing previews. These are read by crawlers without JS execution.

3. Added a `<meta name="description">` tag with the project summary — the single most important SEO element for a site that renders content via JS.

4. Added a `<noscript>` block inside `<body>` containing:
   - An `<h1>` with the project name
   - A `<p>` with the project summary (same text as the meta description)
   - A link to the GitHub repository

5. The `<noscript>` block serves three audiences: search crawlers without JS support, accessibility tools in restricted environments, and users who have JavaScript disabled (rare but nonzero).

6. Total implementation: 8 lines of HTML, no build tools, no SSR framework, no prerendering pipeline.

## Key Insights

- **Meta description + noscript is the minimum viable SEO for a SPA.** Server-side rendering, prerendering, and dynamic rendering are all better solutions, but they require infrastructure. For a portfolio project or internal tool, `<meta description>` + `<noscript>` gets 80% of the value at 1% of the effort.

- **OpenGraph tags are free metadata.** Social sharing previews (LinkedIn, Slack, Twitter) read OG tags from the raw HTML. A SPA without OG tags shows as a blank card when shared. Adding 4 lines of `<meta property="og:...">` tags to the `<head>` fixes this completely.

- **The noscript content should be a summary, not a replica.** Don't try to recreate the full page content in the noscript block — that's what SSR is for. Instead, provide enough content for a crawler to understand what the site is about: title, one-paragraph summary, and a link to the canonical source (GitHub, docs, etc.).

- **Hash-based routing is invisible to crawlers.** URLs like `/#/clusters` and `/#/stats` are treated as the same URL by search engines — everything after `#` is a fragment identifier, not a distinct page. This means the `<noscript>` block on the root page is the *only* crawlable content for the entire site. Make it count.

- **Test with `curl` to see what crawlers see.** Running `curl https://yoursite.com` shows the raw HTML without JS execution. If the output is empty or just a loading spinner, that's what Googlebot's initial pass sees too.

## Examples

Minimal noscript block:
```html
<noscript>
  <div style="padding:2rem;max-width:60ch;margin:auto">
    <h1>Artemis — Calendar Image Selection</h1>
    <p>A data science case study selecting 13 balanced calendar images
       from 12,217 Artemis II mission photographs using statistical
       modeling, visual clustering, and multi-objective scoring.</p>
    <p><a href="https://github.com/user/project">View on GitHub</a></p>
  </div>
</noscript>
```

## Applicability

This applies to any JS-rendered SPA that needs to be discoverable via search engines or shareable via social media. It does NOT apply to sites with server-side rendering (Next.js, Nuxt, etc.) where the HTML already contains the rendered content, or to internal tools that don't need search visibility.

## Metadata

- **Category:** design
- **Block:** block7
- **Tags:** seo, spa, noscript, opengraph, portfolio
