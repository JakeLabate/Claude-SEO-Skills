# Mixed Content / HTTPS Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Mixed Content / HTTPS Audit — {site}

**Date:** {date}
**Scope:** {pages crawled}
**Pages analyzed:** {n} | **Pages with mixed content:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences: is the HTTPS migration complete? Name the dominant source of
insecure resources (often one CDN/host or one template).}

## High-severity issues

### Active mixed content ({n})
Blocked by browsers — these break the page.

| Page | Tag | Insecure resource | Fix |
|---|---|---|---|
| ... | script/link/iframe | http://... | Load over https:// |

### Insecure form actions ({n})
| Page | Form action | Fix |
|---|---|---|
| ... | http://... | Change action to https:// |

## Medium-severity issues

### Passive mixed content ({n})
| Page | Tag | Insecure resource |
|---|---|---|
| ... | img/video/audio | http://... |

## Low-severity issues

{Protocol-relative resources, as a brief list grouped by host.}

## Insecure pages to fix at the source ({n})

| Page served over http | Note |
|---|---|
| ... | redirect to https / fix HSTS |

## Prioritized action list

1. {Highest-impact fix — usually "switch host/CDN X to https", which clears many
   rows at once. Name the host and the affected pages.}
2. ...
```

## Guidance

- Group insecure resources by **host** — one CDN or analytics provider on `http`
  usually explains most rows and is a single fix.
- Lead with active mixed content and insecure forms; those break functionality.
- Every row names the exact page, the tag/attribute, and the insecure URL; the fix
  is almost always "use https://".
- If many pages are served over `http`, the real fix is the site-wide HTTPS
  redirect — note it and point to the `redirect-audit` skill.
- Base everything on the crawled resource inventory; never invent URLs.
