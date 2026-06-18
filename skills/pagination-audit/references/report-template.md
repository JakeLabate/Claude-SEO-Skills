# Pagination Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Pagination Audit — {site}

**Date:** {date}
**Scope:** {pages crawled}
**Pages analyzed:** {n} | **Paginated (page 2+) pages:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences: are paginated series self-canonical and indexable? Name the
dominant problem (most often "every page 2+ canonicalizes to page 1").}

## High-severity issues

### Paginated pages canonicalizing to page 1 ({n})
| Page | Page # | Current canonical | Fix |
|---|---|---|---|
| ... | 2 | {page-1 URL} | Self-canonical to its own URL |

## Medium-severity issues

### Noindexed paginated pages ({n})
| Page | Page # | Fix |
|---|---|---|
| ... | 3 | Make indexable, or ensure items are in the sitemap |

### Paginated pages missing a self-canonical ({n})
{table: page, page #, fix}

### Broken rel=next/prev targets ({n})
{table: page, rel, target, status}

## Low-severity issues

{rel=next/prev reciprocity issues; ?page=1 duplicates. Brief list.}

## Note: rel=next/prev usage ({n} pages)

These pages still declare `rel="next"`/`rel="prev"`. Google no longer uses them
for indexing; harmless to keep, but not a substitute for the fixes above.

## Prioritized action list

1. {Highest-impact fix — usually a single template change making page 2+
   self-canonical and indexable across the whole site. Name the affected sections.}
2. ...
```

## Guidance

- Pagination problems are almost always **template-level** — one fix to the
  listing template clears every paginated page. Frame the action list that way and
  give a couple of example URLs per pattern.
- Lead with the canonical-to-page-1 issue; it's the one that actually de-indexes
  content.
- Every row names the exact URL, its page number, and the corrected behavior.
- Base everything on the crawled inventory; never invent page numbers or targets.
