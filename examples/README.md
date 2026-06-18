# Example reports

These are **illustrative** sample reports showing what each skill produces. They
were written against a fictional site (`example.com`) to demonstrate format,
depth, and the kind of concrete, paste-ready fixes the skills aim for. The
numbers and URLs are invented for the example — a real run reports only what it
observes on your site.

| Example | Skill | Shows |
|---|---|---|
| [`meta-data-audit.md`](meta-data-audit.md) | `meta-data-audit` | Length distribution, duplicate-title groups, paste-ready title/description rewrites |
| [`sitemap-audit.md`](sitemap-audit.md) | `sitemap-audit` | Sitemap index discovery, the "indexable contract", per-URL findings |
| [`internal-link-audit.md`](internal-link-audit.md) | `internal-link-audit` | Orphan pages, click depth, redirect chains, anchor-text quality |

## How a report is produced

1. The collector script crawls/fetches and writes an `*_inventory.json`.
2. The audit script reads that inventory and writes an `audit_report.json` of
   findings grouped by check and severity.
3. Claude turns the findings into the Markdown report you see here, following the
   skill's `references/report-template.md`.

See [`../docs/CONVENTIONS.md`](../docs/CONVENTIONS.md) for the full design.
