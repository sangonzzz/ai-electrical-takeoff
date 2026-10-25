# Module: pdf_context

Owner: Agente 1.

## What it does

Loads one PDF page into a `PageContext`: black/gray stroke segments, black/gray
fills, and text words/spans with font, size, bold, and direction.

## Algorithm

1. Open the page with PyMuPDF (`fitz`).
2. Walk `page.get_drawings()`. For each drawing:
   - Flatten items `l`, `re`, `qu`, and `c` (Bezier sampled into ~8 segments)
     into straight segments.
   - Classify stroke by RGB ≈ (0,0,0) black or ≈ (0.67) gray.
   - Classify fill by RGB ≈ (0,0,0) black or ≈ (0.75) gray.
3. Walk `page.get_text("dict")` lines; use line `dir` for rotation; flag bold
   fonts; split span text into whitespace-separated words (sharing the span bbox).

## Important gotcha

Axis-aligned lines have zero-area `rect`. Never filter drawings with
`rect.intersects(clip)` on raw rects. Use `count_segments_in_box` (inflates by
0.5 pt and tests endpoints / AABB) when clipping for tests or tools.

## Parameters

| Name | Value | Why |
|------|-------|-----|
| `_COLOR_EPS` | 0.05 | Tolerate float color channels |
| `_CURVE_SAMPLES` | 8 | Match ~2 pt median segment length on these plans |

## Known limits

- White fills / other colors are ignored (not needed for electrical layers).
- Word bboxes are span-level, not glyph-precise; room joining is Agente 3's job.
