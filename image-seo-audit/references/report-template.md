# Image SEO Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Image SEO Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **Images found:** {n} | **Alt-text coverage:** {pct}%

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's image health and the biggest wins.}

## High-severity issues

### Missing alt text ({n})

| Page | Image | Suggested alt |
|---|---|---|
| ... | ... | ... |

### Broken images ({n})

| Page | Image | Status |
|---|---|---|
| ... | ... | ... |

## Medium-severity issues

### Missing dimensions ({n})

| Page | Image | Suggested width × height |
|---|---|---|
| ... | ... | ... |

### Oversized files ({n})

| Page | Image | Size | Suggested action |
|---|---|---|---|
| ... | ... | ... | ... |

## Low-severity issues

{One subsection per failing check: not lazy-loaded, legacy format, generic filename, alt too long, redundant alt. Same table style: page, image, current value, suggested fix.}

## Informational

{Empty alt and duplicate alt — list for confirmation, not as defects.}

## Prioritized action list

1. {Highest-impact fix, with exact pages/images and ready-to-apply values}
2. ...
```

## Guidance

- Every issue row must name the exact page URL and image `src`, plus a concrete fix — never generic advice.
- Suggested alt text must describe the image's actual visible content and purpose; never invent details you cannot see. If you cannot determine what an image shows from the page context, say so and ask, rather than guessing.
- Distinguish missing `alt` (a real defect) from intentional `alt=""` (decorative) in the report.
- For lazy-loading recommendations, explicitly exempt the LCP / first above-the-fold image.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Group templated issues (e.g., every product thumbnail missing dimensions from one template) as a single template-level fix with a few example URLs.
- Order the action list by severity first, then by reach (images that appear site-wide or on high-traffic pages first).
- Note the background-image limitation if the user expected images that a crawler cannot see.
