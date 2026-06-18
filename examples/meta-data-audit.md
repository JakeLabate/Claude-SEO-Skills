<!-- Illustrative sample output for the meta-data-audit skill. Fictional data. -->

# Meta Data Audit — example.com

**Date:** 2026-06-18
**Scope:** Crawled from the homepage via sitemap seeds, same-host only.
**Pages crawled:** 142 | **Titles found:** 142 | **Meta descriptions found:** 118

## Summary

| Severity | Issues |
|---|---|
| High | 19 |
| Medium | 27 |
| Low | 6 |

Metadata is templated but largely unfinished: 24 product pages share one title
and one description, and the entire `/blog/tag/` section is missing descriptions.
The highest-impact win is differentiating the product titles — they currently
compete with each other for the same queries.

## Length distribution

| Band | Titles | Descriptions |
|---|---|---|
| Missing | 0 | 24 |
| Too short (< 30 / < 70 chars) | 11 | 9 |
| Good (30–60 / 70–160 chars) | 84 | 71 |
| Too long (> 60 / > 160 chars) | 47 | 14 |

## High-severity issues

### Missing meta descriptions (24)

All under `/blog/tag/*` — the tag template has no description field.

| Page | Suggested description |
|---|---|
| `/blog/tag/onboarding/` | Articles on user onboarding: activation flows, checklists, and first-run UX. 14 posts from the Acme team. (118 chars) |
| `/blog/tag/retention/` | Retention strategy, cohort analysis, and churn-reduction tactics — 9 in-depth posts for SaaS teams. (104 chars) |
| … 22 more (full list in `audit_report.json`) | Template-level fix: add a description field to the tag template. |

### Duplicate titles (1 group, 24 pages)

| Shared title | Pages | Suggested differentiation |
|---|---|---|
| `Acme Widgets — Buy Online` | `/products/widget-a/`, `/products/widget-b/`, … (24) | Interpolate the product name: `{Product Name} — Acme Widgets` |

## Medium-severity issues

### Titles too long (47)

| Page | Current title (length) | Suggested rewrite |
|---|---|---|
| `/blog/the-complete-guide-to…/` | `The Complete Guide to Customer Onboarding for SaaS Companies in 2026` (68) | `The Complete Guide to SaaS Customer Onboarding (2026)` (53) |
| `/pricing/enterprise/` | `Enterprise Pricing Plans and Custom Quotes for Large Teams — Acme` (65) | `Enterprise Pricing & Custom Quotes — Acme` (42) |
| … 45 more | | |

### Titles too short (11)

| Page | Current title (length) | Suggested rewrite |
|---|---|---|
| `/about/` | `About` (5) | `About Acme — Our Team & Mission` (32) |
| `/blog/` | `Blog` (4) | `Acme Blog — SaaS Growth & Onboarding` (37) |

## Low-severity issues

- **Description duplicates title (4):** `/`, `/contact/`, `/demo/`, `/login/`.
- **Keyword stuffing (2):** `/seo-tools/` repeats "seo" 4×; `/widgets/` repeats
  "widgets" 3×.

## Prioritized action list

1. **Differentiate the 24 product titles** (high, ~30% of crawled pages). Change
   the product template to `{Product Name} — Acme Widgets`. Highest traffic
   section; these pages currently cannibalize each other.
2. **Add descriptions to the 24 blog tag pages** (high). Add a description field
   to the tag template; paste-ready values above.
3. **Shorten the 47 over-length titles** (medium). Start with the 12 pages in
   `/pricing/` and `/products/` (highest intent). Rewrites above.
4. **Expand the 11 thin titles** (medium), starting with `/about/` and `/blog/`.
5. **Resolve low-severity duplication and stuffing** (low) as cleanup.

> Full machine-readable findings: `audit_report.json`. Tables capped at a few
> rows here; the JSON lists every affected URL.
