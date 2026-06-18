# Heading Structure Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Heading Structure Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **Headings found:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's heading health and the biggest wins.}

## High-severity issues

### Missing H1 ({n})

| Page | Suggested H1 |
|---|---|
| ... | ... |

### No headings ({n})

| Page | Suggested outline |
|---|---|
| ... | ... |

## Medium-severity issues

### Multiple H1s ({n})

| Page | H1 values | Suggested fix |
|---|---|---|
| ... | ... | ... |

### Skipped levels ({n})

| Page | Jump | Heading | Suggested fix |
|---|---|---|---|
| ... | h2 → h4 | ... | demote to h3 |

### Empty headings ({n})

| Page | Level |
|---|---|
| ... | ... |

## Low-severity issues

{One subsection per failing check: first-not-H1, long heading, duplicate heading. Same table style: page, current value, suggested fix.}

## Informational

{Title/H1 mismatches and deep-outline notes — list for confirmation, not as defects.}

## Prioritized action list

1. {Highest-impact fix, with exact pages and ready-to-apply heading values}
2. ...
```

## Guidance

- Every issue row must name the exact page URL and the offending heading(s), plus a concrete fix — never generic advice.
- Suggested headings must reflect the page's actual content (use the existing headings and title from the inventory as context); never invent topics the page does not cover.
- For skipped-level and multiple-H1 issues, recommend the specific level change (e.g., "change this H4 to H3") rather than restating the rule.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Group templated issues (e.g., every blog post missing an H1 from one template) as a single template-level fix with a few example URLs.
- Order the action list by severity first, then by traffic impact (high-traffic and high-intent pages first).
- If a page reports no headings but visibly looks structured, flag the likely cause: section titles styled with CSS instead of real heading tags.
