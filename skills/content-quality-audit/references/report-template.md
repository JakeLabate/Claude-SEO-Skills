# Content Quality Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Content Quality Audit — {site}

**Date:** {date}
**Scope:** {pages crawled}
**Pages analyzed:** {n} | **Median word count:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences: overall content depth (use the median word count), and the
dominant problem (e.g. a large set of near-duplicate templated pages).}

## High-severity issues

### Thin content ({n})
| Page | Words | Suggested action |
|---|---|---|
| ... | 84 | Expand / consolidate / noindex |

### Duplicate content ({n} groups)
| Pages | Words | Suggested action |
|---|---|---|
| {url1}, {url2}, … | 320 | Canonicalize / consolidate / differentiate |

## Medium-severity issues

### Near-duplicate content ({n} pairs)
| Pages | Similarity | Suggested action |
|---|---|---|
| {url1} ↔ {url2} | 0.92 | Add unique content or consolidate |

### Low text-to-HTML ratio ({n})
{table: page, ratio, words}

## Low-severity issues

### Missing H1 ({n})
{brief table}

## Prioritized action list

1. {Highest-impact fix — usually a template-level near-duplicate cluster or a set
   of thin pages to consolidate. Name the pattern and example URLs.}
2. ...

> Note: this audit does not execute JavaScript. Verify that any flagged page isn't
> simply rendered client-side before treating it as thin or empty.
```

## Guidance

- **Calibrate to the site.** State the threshold used and the median word count so
  the user can judge whether "thin" is fair for their content type.
- Group near-duplicate and thin pages into **patterns** (e.g. "120 location pages
  share one template") with a single recommended fix and example URLs.
- Distinguish *fix the content* from *noindex it* — not every thin page should
  rank; some should simply be removed from the index.
- Always caveat JavaScript-rendered pages.
- Base everything on the measured signals; never invent word counts or content.
