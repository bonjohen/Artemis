# Lesson 049: Drag-and-Drop as the Simplest Viable Interaction

## The Lesson

When the user's mental model is "put this thing in that slot," drag-and-drop is less code and more intuitive than alternatives like dropdowns, search dialogs, or multi-step wizards. The key is spatial co-visibility: the source pool and target slots must be on screen simultaneously so the user can see both what's available and where it goes.

## Context

A calendar selection tool needed to let users assign images to 13 monthly slots. The original implementation required navigating to a separate candidates page, clicking "use as starting point" to copy a preset into sessionStorage, then navigating to the selection page. There was no way to browse the full image collection and assign individual images to specific months. The user wanted to drag images from a browsable pool directly into calendar slots.

## What Happened

1. The original selection page had a 13-slot grid and a sidebar with scores. Slots could only be populated by loading a candidate method or a saved selection. No direct image-to-slot assignment was possible.

2. Rebuilt with a two-column layout: calendar slots on the left, scrollable image pool on the right. Both visible simultaneously — no tab switching, no modals, no page navigation.

3. Used the HTML5 Drag and Drop API directly:
   - Pool images: `draggable=true`, `dragstart` sets `dataTransfer` with image metadata as JSON
   - Slot targets: `dragover` (preventDefault to allow drop), `dragleave`, `drop` (parse JSON, assign to slot)
   - Slots with images: the image itself is also draggable, enabling rearrangement between slots

4. Added a method dropdown at the top to pre-populate all 13 slots from a candidate method (A–E), giving users a starting point they can then modify by dragging.

5. Added per-slot controls: an `×` button to remove an image, and a cover checkbox (radio-like — at most one checked across all slots) to designate which month's image is the calendar cover.

6. Scores update live after each drop — the user sees immediately how adding or rearranging an image changes the objective function, diversity, month fit, etc.

## Key Insights

- **Co-visibility eliminates navigation.** The original workflow required three page transitions (browse → candidates → selection). Putting the pool and slots side-by-side reduces this to zero transitions. The cognitive cost of "where do I go to do this?" disappears entirely.
- **HTML5 drag-and-drop is sufficient for structured data.** The API is verbose but complete. `dataTransfer.setData('text/plain', JSON.stringify(data))` on dragstart and `JSON.parse(e.dataTransfer.getData('text/plain'))` on drop handles all the data passing. No drag-and-drop library was needed.
- **Dimming assigned images in the pool prevents confusion.** Images already in a slot get `opacity: 0.35` in the pool grid. Without this, users drag the same image into two slots and wonder why the first slot emptied.
- **Live scoring makes drag-and-drop exploratory.** Because scores update after every drop, users naturally experiment: "what if I swap this Earth shot for that Moon shot?" The interaction becomes a conversation with the objective function rather than a one-shot assignment.
- **Pre-population plus modification beats blank-canvas building.** Starting from a method (e.g., "MMR Greedy") and swapping 2-3 images is faster and produces better results than building a calendar from scratch. The method dropdown bridges the gap between algorithmic optimization and human judgment.

## Applicability

Drag-and-drop is the right interaction when:
- The task is spatial assignment (items → slots, files → folders, cards → columns)
- Source and target can be on screen simultaneously (small-to-medium item counts)
- The user benefits from seeing the result update in real time
- Items are visually identifiable (images, cards with thumbnails)

Does NOT apply when:
- The item count is too large for visual scanning (10,000+ items need search, not browsing)
- Touch devices are the primary target (HTML5 drag-and-drop has poor mobile support)
- The assignment has complex constraints that need validation before dropping (use a confirmation dialog instead)
- The user's mental model isn't spatial (e.g., configuring numeric parameters, writing text)

## Related Lessons

- [Lesson 033: Vanilla JS SPA Without a Build Step](../block5/033_vanilla_js_spa_no_build_step.md) — the selection builder uses the same zero-toolchain approach; HTML5 APIs are sufficient without React DnD or similar libraries
