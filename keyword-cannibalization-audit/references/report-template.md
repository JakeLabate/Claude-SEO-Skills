# Keyword Cannibalization Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Keyword Cannibalization Audit — {site}

**Date:** {date}
**Scope:** {pages crawled}
**Pages analyzed:** {n} | **Overlap threshold:** {jaccard}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentences: how much overlap exists, and the most significant competing
cluster. Remind the reader these are candidates to confirm, not automatic merges.}

## High-severity: duplicate title targets ({n})

| Shared target | Competing pages | Suggested resolution |
|---|---|---|
| "customer onboarding" | /a/, /b/, /c/ | Pick the primary; merge/redirect/differentiate the rest |

## Medium-severity: overlapping target clusters ({n})

### Cluster {i} — {shared keywords}
| Page | Title | Role |
|---|---|---|
| ... | ... | primary / supporting / consolidate |

**Recommended hierarchy:** {which page is primary, which support it, which to merge.}

{Repeat per cluster, largest first.}

## Low-severity: shared title phrases ({n})

{Brief table of pages sharing a significant title bigram, for review.}

## Prioritized action list

1. {The highest-value cluster to resolve, naming the primary page and what to do
   with each competitor. Confirm against Search Console query data first.}
2. ...
```

## Guidance

- **Frame as hierarchy, not deletion.** For each cluster, recommend one primary
  page and a role for every other page (support / differentiate / merge / redirect)
  — don't blanket-recommend removing pages.
- **Always say "confirm with query data."** This audit infers competition from
  on-page signals; Search Console (or analytics) confirms whether URLs actually
  swap for the same query.
- Order clusters by size and by the value of the query they target.
- Pass `--brand-suffix` so brand words don't create false overlap.
- Base every grouping on the observed signatures; never invent rankings.
