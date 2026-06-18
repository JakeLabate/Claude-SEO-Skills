<!-- Illustrative sample output for the internal-link-audit skill. Fictional data. -->

# Internal Link Audit — example.com

**Date:** 2026-06-18
**Scope:** Crawled 142 same-host pages from the homepage; built the internal link graph.
## Summary

| Severity | Issues |
|---|---|
| High | 14 |
| Medium | 22 |
| Low | 31 |

The link graph is shallow and hub-heavy: the blog is well interlinked, but 17
product pages are orphaned (reachable only from the XML sitemap, not from any
internal link) and 9 high-value pages sit at click depth 4+. Fixing orphans and
flattening depth will spread link equity to the pages that monetize.

## Graph overview

| Metric | Value |
|---|---|
| Pages crawled | 142 |
| Internal links | 1,876 |
| Orphan pages (0 inbound internal links) | 17 |
| Avg. click depth from homepage | 2.8 |
| Max click depth | 5 |
| Broken internal links | 11 |
| Redirecting internal links | 34 |

## High-severity issues

### Orphan pages (17)

Reachable from the sitemap but not linked from any page — they accrue almost no
internal equity.

| Orphan page | Suggested link source |
|---|---|
| `/products/widget-g/` | Link from `/products/` category grid |
| `/blog/2024/launch-recap/` | Link from `/blog/` index and related posts |
| … 15 more | |

### Broken internal links (11)

| Linking page | Broken target | Status | Fix |
|---|---|---|---|
| `/blog/onboarding-guide/` | `/resources/checklist.pdf` | 404 | Update or remove the link |
| `/` (footer) | `/webinars/` | 404 | Page was removed; drop the footer link |
| … 9 more | | | |

## Medium-severity issues

### Redirecting internal links (34)

Internal links pointing at URLs that 301 elsewhere — each wastes a hop and a
little equity. Update the `href` to the final destination.

| Linking page | Link target | Redirects to |
|---|---|---|
| `/` (nav) | `/blog` | `/blog/` (trailing-slash 301) |
| `/products/widget-a/` | `/support` | `/help/` |
| … 32 more | | |

### Deep pages (click depth ≥ 4) (9)

| Page | Depth | Suggested shortcut |
|---|---|---|
| `/products/widget-a/specs/datasheet/` | 5 | Link datasheets from the product page directly |
| … 8 more | | |

## Low-severity issues

- **Generic anchor text (31):** "click here" (12), "read more" (14), "learn
  more" (5). Replace with descriptive, keyword-relevant anchors.
- **Pages with a single inbound link (19):** fragile; add contextual links.

## Prioritized action list

1. **Link the 17 orphan product/blog pages** from their category and related
   sections (high). Biggest equity redistribution.
2. **Fix the 11 broken internal links** (high) — update targets or remove.
3. **Repoint the 34 redirecting links to final URLs** (medium); most are the
   trailing-slash 301, fixable in the nav template.
4. **Flatten the 9 deep pages to ≤ 3 clicks** (medium) with contextual links.
5. **Rewrite the 31 generic anchors** (low) to descriptive text.

> The full link graph (inbound/outbound per URL, depths, anchors) is in
> `link_graph.json`; findings are in `audit_report.json`.
