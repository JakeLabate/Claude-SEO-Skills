# Conventions & design

This document explains how every skill in this repository is built. If you want
to understand how the audits work, read this first; if you want to add a skill,
follow this pattern so it behaves like the rest.

## The fetch → extract → audit → report pipeline

Every skill separates **gathering data** from **judging it** from **explaining
it**. This is the single most important idea in the repo.

```
            fetch (shared scripts/fetch_pages.py)
                │   crawls the site ONCE, stores raw HTML + response facts
                ▼
        page_cache.json  ← a raw, audit-agnostic snapshot of what was served
                │
            extract (a *.py "extract"/"collect" script, --from-cache)
                │   pure: parses the cached HTML for the fields THIS audit needs
                ▼
        inventory.json  ← a plain, reviewable snapshot of what exists
                │
            audit (a *.py "audit" script)
                │   applies checks + thresholds, assigns severities
                ▼
         audit_report.json  ← findings grouped by check, with a summary
                │
            report (Claude, guided by SKILL.md + report-template.md)
                ▼
         a human-readable Markdown report with prioritized fixes
                │
            export (optional — scripts/md_to_docx.py)
                ▼
         the same report as a Word .docx, for sharing
```

**Fetch is split out from extract** so a site is crawled a single time and every
audit reads from the same `page_cache.json`. A full SEO audit then fetches once
and extracts many times, instead of crawling the site once per area. Each
crawl-based extractor accepts `--from-cache page_cache.json` (pure, no network)
*and* keeps its standalone modes (a live URL, `--local`, `--url-list`) for
single-area runs, where fetch+extract collapse back into one step.

Two skills opt out of the shared cache on purpose: `internal-link-audit` and
`site-architecture-audit` build a link graph that needs per-page crawl **depth**
and status resolution of linked-but-uncrawled targets, which a flat page cache
does not model. They keep their own crawler.

Why split it this way:

- **`fetch_pages.py` makes the network calls; extract and audit are pure.** You
  can re-extract, re-run the audit, tweak thresholds, or diff two runs without
  re-crawling. Extract and audit are deterministic and easy to reason about.
- **The inventory is the source of truth.** Every finding traces back to an
  observed fact in the inventory — never to a guess. The reporting step is told,
  explicitly, to never invent URLs, prices, or claims.
- **Claude does the judgment that needs context** (writing replacement titles,
  prioritizing by traffic), while the scripts do the judgment that should be
  mechanical (counting characters, comparing hosts, resolving redirects).

## Anatomy of a skill

```
skill-name/
├── SKILL.md                     # YAML frontmatter (name, description) + workflow
├── references/
│   ├── audit-checks.md          # every check: definition, why it matters, fix
│   └── report-template.md       # the exact Markdown structure of the output
└── scripts/
    ├── fetch_pages.py                # shared: crawl once → page_cache.json (crawl skills)
    ├── extract_*.py / collect_*.py   # the extractor → inventory.json (reads --from-cache)
    ├── audit_*.py                    # the auditor → audit_report.json
    └── md_to_docx.py                 # shared: render the report as a .docx
```

### `SKILL.md`

- **Frontmatter** has a `name` (must equal the folder name) and a `description`.
  The description is what Claude matches a user request against, so it names the
  problems the skill finds *and* the trigger phrases ("audit, validate, check,
  fix …"). Keep it specific and keyword-rich.
- **Body** follows a fixed shape: *When to use this skill* → *Inputs to collect*
  → *Workflow* (numbered steps that run the scripts) → a checks table with
  severities → *Produce the report* → *Recommend fixes* → *Resources*.

### `references/audit-checks.md`

One entry per check, grouped by severity, each with three parts:
**Definition** (what triggers it), **Why it matters** (the SEO rationale), and
**Fix** (the concrete remedy). This file is the spec the auditor implements and
the rationale Claude cites in the report.

### `references/report-template.md`

The literal Markdown skeleton of the final report plus a *Guidance* section. The
guidance always enforces: name the exact URL and current value, give a concrete
replacement, cap tables (~20 rows) and offer the full list, and never invent
facts.

## The severity model

Every finding is one of four levels, applied consistently across skills:

| Severity | Meaning | Examples |
|---|---|---|
| **High** | Actively harms indexing/ranking or breaks the page. Fix first. | Missing title, sitemap URL 404s, `Disallow: /`, broken canonical |
| **Medium** | Real SEO quality problem, not an emergency. | Title too long, canonicalizes elsewhere, slow LCP proxy |
| **Low** | Hygiene / polish. | Invalid `changefreq`, generic filename, future `lastmod` |
| **Info** | Worth a look, not counted as an issue. | Title/H1 divergence, intentional patterns |

The auditor emits a `severity` map and an `issues_by_severity` summary so the
report can lead with what matters.

## The "indexable contract"

A recurring principle the skills enforce: **every URL you submit to search
engines (in a sitemap, an internal link, a canonical) should be a final,
canonical, indexable `200` page.** A URL that redirects, 404s, is noindexed, is
blocked by robots.txt, or canonicalizes elsewhere violates that contract and is
flagged. Many checks across the sitemap, redirect, internal-link, and
canonical audits are specific applications of this one idea.

## Standard-library only

**The Python scripts depend on nothing but the Python standard library.** No
`pip install`, no virtualenv — if you have Python 3.8+, they run. This is a
deliberate constraint:

- HTML is parsed with `html.parser.HTMLParser`, XML with
  `xml.etree.ElementTree`, HTTP with `urllib.request`, gzip with `gzip`.
- The only optional dependency is `brotli`, and it is imported defensively
  (`try/except`) — present means Brotli-compressed responses get decoded, absent
  means that one check is skipped. Nothing else is optional because nothing else
  is needed.

If you add a skill, keep this guarantee. If a check truly cannot be done with the
stdlib, make the dependency optional and degrade gracefully.

## Exporting the report as a .docx

The reporting step produces Markdown. When a user wants a shareable Word
document, `scripts/md_to_docx.py` converts that Markdown into a `.docx`:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

It honors the stdlib-only guarantee — a `.docx` is a ZIP of OOXML parts, so the
converter builds those parts with `zipfile` and string templates, no
dependency. It renders headings, paragraphs, tables, bullet/numbered lists,
links, bold/italic, inline code, blockquotes, and code blocks; anything fancier
degrades to plain text rather than failing. The conversion runs *after* the
report so Claude's judgment (prioritized fixes, rewritten titles) is preserved —
the `.docx` is the report, reformatted, not a re-derivation from the JSON.

## Shared scripts (and how they stay in sync)

Two scripts are shared across skills and must be byte-identical everywhere they
appear. They have to be: the installer (`bin/cli.js`) copies skill folders
**individually**, so a script in `tools/` alone would not exist for someone who
installs just one skill. Skills are self-contained.

- `md_to_docx.py` — the Markdown→.docx converter — goes into **every** skill.
- `fetch_pages.py` — the shared crawl-once fetch stage — goes into the
  **crawl-based** skills that read its cache via `--from-cache`, plus the
  `full-seo-audit` orchestrator that runs it once.

The canonical copies live in `tools/`. The manifest of which file lands in which
skills is `SHARED` in `tools/sync_shared.py`. `tools/sync_shared.py` stamps each
file into its target `skills/*/scripts/`, and `tools/validate_skills.py` (which
imports that same manifest) fails if any required copy drifts or is missing. So:
**edit `tools/<file>.py`, then run `python3 tools/sync_shared.py`** — never edit
a per-skill copy directly. To add a skill to the page-cache set, add its name to
`CACHE_SKILLS` in `tools/sync_shared.py` and re-run the sync.

## Shared script conventions

These patterns recur in every collector and are worth copying verbatim:

- `USER_AGENT` and `TIMEOUT` module constants; identify the bot honestly.
- `fetch(url) -> (status, final_url, body)` where `status == 0` means a
  network/connection error and `body` is `None` for non-HTML or failures.
- An `HTMLParser` subclass that extracts exactly what the audit needs and nothing
  more.
- Same-host BFS crawl, seeded from the sitemap when available, capped by
  `--max-pages`.
- Three input modes where it makes sense: a live URL (crawl), `--local` (a folder
  of HTML files), and `--url-list` (a text file of URLs).
- Collectors write a single `*_inventory.json`; auditors read it and write
  `{ "summary": …, "severity": …, "findings": … }`.
- Progress goes to `stderr` (`print(..., file=sys.stderr)`), data goes to the
  JSON file, and the summary is echoed to `stdout`.

## Adding a new skill (checklist)

1. Create `skills/skill-name/` with `SKILL.md`, `references/`, and `scripts/`.
2. Write the collector and auditor following the conventions above.
3. Document every check in `references/audit-checks.md` and the output shape in
   `references/report-template.md`.
4. Add the skill to the table in `README.md`. (The CLI and npm package pick it
   up automatically — `bin/cli.js` scans `skills/` for a `SKILL.md`, and
   `package.json` ships the whole `skills/` folder.)
5. Run `python3 tools/sync_shared.py` to drop the shared `md_to_docx.py` into the
   new skill's `scripts/`.
6. Run `python3 tools/validate_skills.py` until it passes.
