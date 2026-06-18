# Full SEO Audit Report Template

Use this structure for the consolidated report delivered to the user.

```markdown
# Full SEO Audit — {site}

**Date:** {date}
**Scope:** {pages crawled, sitemap URLs probed, areas audited}
**Areas audited:** {n} of {total}

## Executive summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{3–5 sentences: overall health, the single biggest theme (e.g. an incomplete
http→https migration), and the highest-impact fixes.}

**Top 5 fixes (across all areas):**

1. {Highest-impact fix, the area(s) it touches, and the pages affected}
2. ...

## Scorecard

| Area | High | Medium | Low | Status |
|---|---|---|---|---|
| Sitemaps | {n} | {n} | {n} | 🔴 / 🟡 / 🟢 |
| robots.txt | … | … | … | … |
| Internal links | … | … | … | … |
| Metadata | … | … | … | … |
| … one row per audited area … | | | | |

## Findings by area

### {Area name}

{2–4 sentence summary of this area's top issues, with counts. Link to or inline
the area's detailed report. Do not repeat every row here — point to the per-skill
report for the full list.}

{Repeat per audited area, ordered by severity of findings.}

## Prioritized roadmap

Ordered by impact across all areas, not by which audit found the issue.

1. **{Fix}** — {severity}, {pages/areas affected}. {One line on why it's first.}
2. ...

### Quick wins (low effort, real impact)

- {Bulleted shortlist of cheap fixes}

### Root-cause groupings

- **{e.g. http→https migration}** surfaces across {sitemap, redirects, internal
  links, canonical, mixed content}. Fix once at the source: {the fix}.
```

## Guidance

- **Prioritize across areas, not within them.** A single template bug affecting
  500 pages outranks a worse-sounding issue on one page. Indexation blockers
  (robots, noindex, broken canonicals, dead sitemap URLs) come before on-page
  polish.
- **Collapse duplicated root causes.** The same migration or template defect
  often trips several audits; present it once with all the symptoms it explains.
- **Don't drown the reader.** The consolidated report summarizes; the per-skill
  reports hold the exhaustive tables. Link to them.
- **Every claim traces to data.** Pull counts from `consolidated_report.json` and
  specifics from each skill's `audit_report.json`. Never invent URLs or numbers.
- **State coverage honestly.** List which areas were audited and which were
  skipped (and why — e.g. "Core Web Vitals field data skipped: no PSI key").
