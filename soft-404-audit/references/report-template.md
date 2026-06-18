# Soft 404 Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Soft 404 Audit — {site}

**Date:** {date}
**Scope:** {pages crawled}
**Pages analyzed:** {n} | **Missing-page probe returned:** {status}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences. State the headline first: does the site return a real 404 for
missing URLs, or 200 for everything? Then the count of specific soft 404s found.}

## High-severity issues

### Site-wide: missing URLs return 200 (if applicable)
{If the probe returned 200, explain that every unknown URL becomes an indexable
soft 404, and that this is a single server/router fix.}

### Soft 404s (error pages served as 200) ({n})
| Page | Title / H1 | Words | Fix |
|---|---|---|---|
| ... | "Page not found" | 12 | Return 404, or restore the page |

## Medium-severity issues

### Thin pages matching the error template ({n})
| Page | Title | Words | Fix |
|---|---|---|---|
| ... | ... | 8 | Confirm should exist; else return 404 |

## Low-severity issues

### Empty / near-empty pages ({n})
{Brief table. Note which may be JavaScript-rendered and need manual verification.}

## Prioritized action list

1. {If the probe returned 200: fix the server/router to return real 404s — this is
   the top fix and clears the whole class. Otherwise lead with the confirmed soft
   404s.}
2. ...
```

## Guidance

- **Lead with the status-code behavior.** "Missing URLs return 200" is a single
  root-cause fix that outranks any individual page.
- Distinguish *confirmed* soft 404s (error phrase) from *suspected* ones (thin /
  template-matching) so the user knows what's certain.
- Flag that JavaScript-rendered pages can look thin to this crawler; recommend
  manual verification before returning 404 on a borderline page.
- Every row names the exact URL, the observed title/word count, and the fix.
- Base everything on the crawled signals; never invent page content.
