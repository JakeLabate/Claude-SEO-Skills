# Open Graph / Twitter Card Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Open Graph / Social Metadata Audit — {site}

**Date:** {date}
**Scope:** {pages crawled, share images probed}
**Pages analyzed:** {n} | **Share images probed:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences: do pages have complete, valid OG tags with working images? Name
the dominant gap.}

## High-severity issues

### Missing og:image / broken og:image ({n})
| Page | Problem | Fix |
|---|---|---|
| ... | no og:image / 404 image | Add/repair an absolute 1200×630 https image |

### Missing og:title ({n})
| Page | Suggested og:title |
|---|---|
| ... | ... |

## Medium-severity issues

{Subsections for missing og:description, missing/mismatched og:url, non-image or
relative og:image. Table with page, current value, corrected value.}

## Low-severity issues

{twitter:card gaps, over-length og:title/og:description, as a brief list.}

## Shared / default images to review ({n})

| Share image | Pages using it | Note |
|---|---|---|
| ... | {n} | brand default vs. should be page-specific |

## Prioritized action list

1. {Highest-impact fix with exact pages and concrete values}
2. ...
```

## Guidance

- Lead with broken and missing images — those have the most visible impact on
  shares.
- Every row names the exact page, the current value, and a concrete replacement.
  Suggested `og:image` URLs must be absolute `https://`.
- Group template-level gaps (e.g. the whole blog missing `og:image`) as one fix.
- Treat duplicate/default images as a judgement call to surface, not a defect.
- Base every status on the probed image data; never assume an image works.
