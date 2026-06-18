# Canonical Tag Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Canonical Tag Audit — {site}

**Date:** {date}
**Scope:** {pages crawled, canonical targets probed}
**Pages analyzed:** {n} | **Canonical targets probed:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview: are canonicals present, self-referencing, and pointing at
live indexable URLs? Name the dominant problem.}

## High-severity issues

### Missing canonical ({n})
| Page | Suggested canonical |
|---|---|
| ... | self-referencing absolute URL |

### Canonical points to non-200 / redirect ({n})
| Page | Canonical target | Problem | Fix |
|---|---|---|---|
| ... | ... | 404 / 301→{dest} | Point at the final 200 URL |

### Multiple / conflicting canonicals ({n})
| Page | Canonicals found | Fix |
|---|---|---|
| ... | {url1}, {url2} | Keep one |

## Medium-severity issues

{One subsection per failing check: relative, cross-host, protocol downgrade,
canonical-to-noindex, header/HTML conflict. Table with page, current canonical,
and the corrected value.}

## Low-severity issues

{Fragment-in-canonical and similar hygiene, as a brief list.}

## Non-self canonicals to confirm ({n})

| Page | Canonicalizes to | Looks intentional? |
|---|---|---|
| ... | ... | confirm with the user |

## Prioritized action list

1. {Highest-impact fix with exact pages and the corrected canonical value}
2. ...
```

## Guidance

- Every row names the exact page, its current canonical, and the corrected
  absolute URL.
- Treat **non-self canonicals** as items to confirm, not defects — list them so
  the user can verify each consolidation is intended.
- Group template-level problems (e.g. every paginated page canonicalizing to page
  1) as a single fix with example URLs.
- Base everything on the probed data in the inventory; never invent target
  statuses.
