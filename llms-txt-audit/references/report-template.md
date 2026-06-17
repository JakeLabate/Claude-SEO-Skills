# llms.txt Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# llms.txt Audit — {site}

**Date:** {date}
**File:** {status} | **Sections:** {n} | **Links:** {found} ({probed} probed) | **llms-full.txt:** {yes/no}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of llms.txt health and the biggest wins. If the file is
missing entirely, say so up front and frame the report as "how to create one".}

## File structure

| Element | Status |
|---|---|
| H1 title | "Project Name" / missing |
| Summary blockquote | present / missing |
| Sections | Docs, Guides, Optional |
| Content-Type | text/markdown |
| /llms-full.txt | present / missing |

## High-severity issues

### Availability / structure ({n})

{Call out a missing file, an HTML-served file, or a missing H1 with the fix.}

### Broken links ({n})

| URL | Status | Section | Action |
|---|---|---|---|
| ... | 404 | Docs | Replace with live URL or remove |

## Medium-severity issues

### Redirecting links ({n})

| URL | Status | Final URL | Action |
|---|---|---|---|
| ... | 301 | ... | Replace with final URL |

### Link descriptions & formatting ({n})

| Item | Problem | Fix |
|---|---|---|
| - [API](…) | no description | Add `: what this link is` |
| - plain text line | not a markdown link | Rewrite as `- [title](url): desc` |

### Other ({n})

{One row per failing check: missing summary, wrong host, noindex/blocked links,
redirecting /llms.txt, wrong content type. Same style: item, problem, fix.}

## Low-severity issues

{Brief list: relative URLs, no sections/links, duplicate links, llms-full.txt absent.}

## Suggested llms.txt

\`\`\`markdown
# {Project Name}

> {One-line summary.}

## {Section}
- [{Title}](https://example.com/{path}): {description}
\`\`\`

{Provide a corrected or starter file when the existing one is missing or weak.}

## Prioritized action list

1. {Highest-impact fix, with the exact link or line to add/remove/change}
2. ...
```

## Guidance

- If `/llms.txt` is missing, lead with that and deliver a ready-to-use starter file in the "Suggested llms.txt" block rather than a list of defects.
- Every issue row must name the exact URL or list item and a concrete action ("replace with {final URL}", "add `: description`", "use absolute URL").
- Reinforce the core rule in the summary: llms.txt links should point to final, canonical, reachable `200` pages, each with a clear description.
- Provide a corrected or starter markdown block so the user can copy-paste the fix.
- Treat `/llms-full.txt` as optional — note its absence, but do not present it as a defect unless the user wants full-content ingestion.
- Cap link tables at ~20 rows in the report body; offer the full list (CSV/JSON) if larger.
- Order the action list by severity first, then by how many links each fix repairs.
