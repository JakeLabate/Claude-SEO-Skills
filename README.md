# Claude-SEO-Skills

[![npm version](https://img.shields.io/npm/v/claude-seo-skills.svg)](https://www.npmjs.com/package/claude-seo-skills)
[![CI](https://github.com/JakeLabate/Claude-SEO-Skills/actions/workflows/ci.yml/badge.svg)](https://github.com/JakeLabate/Claude-SEO-Skills/actions/workflows/ci.yml)
[![license](https://img.shields.io/npm/l/claude-seo-skills.svg)](LICENSE)

A collection of [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) for SEO tasks. Each folder under [`skills/`](skills/) is a self-contained, fully functional Claude skill.

Each skill performs a real technical-SEO audit — crawling a site (or scanning local HTML), checking it against documented rules, and producing a prioritized, paste-ready report. They're built to be **read and learned from** as much as run: the rationale behind every check lives in each skill's `references/audit-checks.md`.

- **See what they produce:** [`examples/`](examples/) — illustrative sample reports.
- **Understand how they work:** [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — the design behind every skill.

## Requirements

- **Python 3.8+** to run the audit scripts. **No `pip install` required** — every script uses only the Python standard library. (The one optional dependency, `brotli`, is used if present and skipped if not.)
- **Node 16+** only if you use the `npx` installer below. Claude itself runs the skills; you don't need Node to use them once installed.

## Skill architecture

Every skill folder follows the standard Claude skill structure:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter (name, description) + instructions
├── references/       # Optional: reference docs loaded as needed
└── scripts/          # Optional: executable scripts the skill can run
```

All skills share one pipeline — **collect → audit → report** — and a four-level severity model (High / Medium / Low / Info). See [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) for the full design and a guide to adding your own skill.

## Run everything at once

| Skill | Description |
|---|---|
| [`full-seo-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/full-seo-audit) | **Orchestrator.** Runs every individual audit below and consolidates the findings into one prioritized, cross-area report — ranked by impact, not by which audit found the issue. Use for a complete / comprehensive technical-SEO review. |

## Available skills

| Skill | Description |
|---|---|
| [`canonical-tag-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/canonical-tag-audit) | Audit a website's `rel="canonical"` tags: missing canonicals, multiple/conflicting canonicals, canonicals pointing at non-200/redirecting/noindexed URLs, relative or cross-host canonicals, https-to-http downgrades, and Link-header/HTML conflicts. |
| [`content-quality-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/content-quality-audit) | Audit a website's content quality: thin content, exact-duplicate body text, near-duplicate (templated) pages via MinHash similarity, low text-to-HTML ratio, and missing H1s. |
| [`core-web-vitals-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/core-web-vitals-audit) | Audit a website's Core Web Vitals and page-experience signals (LCP, CLS, INP, TTFB): optionally pulls real field data from Google PageSpeed Insights (CrUX), and always collects browserless lab proxies — render-blocking CSS/JS, page weight, image dimension and lazy-loading hygiene, TTFB, text compression, DOM size, request counts, and third-party origins. |
| [`external-link-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/external-link-audit) | Audit a website's external (outbound) links: broken links, redirected targets, insecure HTTP links, affiliate `rel="sponsored"` compliance, unsafe `target="_blank"` usage, and sitewide outbound link patterns. |
| [`heading-structure-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/heading-structure-audit) | Audit a website's heading hierarchy (H1–H6): missing or multiple H1s, skipped heading levels, empty headings, headings that don't start at H1, overly long headings, and duplicate headings. |
| [`image-seo-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/image-seo-audit) | Audit a website's images for SEO and Core Web Vitals: missing or empty alt text, missing `width`/`height` (layout shift), no lazy loading, oversized files, legacy formats, generic filenames, and broken image URLs. |
| [`internal-link-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/internal-link-audit) | Audit a website's internal linking structure: broken links, orphan pages, redirect chains, click depth, anchor text quality, and link equity distribution. |
| [`keyword-cannibalization-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/keyword-cannibalization-audit) | Audit a website for keyword cannibalization: pages with duplicate title targets, clusters of pages whose title/H1/keyword signatures overlap, and pages sharing the same primary keyword phrase — with a recommended page hierarchy. |
| [`llms-txt-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/llms-txt-audit) | Audit a website's `/llms.txt` for AI/LLM discoverability (per llmstxt.org): a missing or HTML-served file, missing required H1 title or summary blockquote, broken/redirecting/blocked links, links missing descriptions, malformed list items, wrong-host or relative URLs, duplicate links, wrong content type, and whether a companion `/llms-full.txt` exists. |
| [`meta-data-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/meta-data-audit) | Audit a website's title tags and meta descriptions: missing, duplicate, too-long, too-short, or multiple tags, generic or boilerplate titles, and keyword stuffing. |
| [`mixed-content-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/mixed-content-audit) | Audit an HTTPS website for mixed content: active mixed content (http scripts/styles/iframes browsers block), insecure form actions, passive mixed content (http images/media), legacy protocol-relative URLs, and pages still served over http. |
| [`open-graph-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/open-graph-audit) | Audit a website's Open Graph and Twitter Card metadata: missing og:title/description/image/url, broken or non-image or relative og:image, og:url mismatching the canonical, missing twitter:card, over-length social titles/descriptions, and reused default images. |
| [`pagination-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/pagination-audit) | Audit a website's pagination: paginated pages canonicalizing to page 1 (hiding deep content), noindexed component pages, paginated pages missing a self-canonical, broken or inconsistent rel=next/prev, and redundant ?page=1 first pages. |
| [`redirect-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/redirect-audit) | Audit a website's redirects: resolves the full redirect chain for every URL to find chains and loops, redirects that end in 404s/errors, temporary (302) redirects used for permanent moves, HTTPS-to-HTTP downgrades, client-side meta-refresh and JavaScript redirects, dropped query strings, and canonicals pointing at redirecting URLs. |
| [`robots-txt-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/robots-txt-audit) | Audit a website's robots.txt: a redirected or HTML-served file, a 5xx read as "block everything", a sitewide `Disallow: /`, syntax errors, render-blocking CSS/JS, missing or unreachable `Sitemap:` directives, a missing default `User-agent: *` group, unsupported directives (noindex, crawl-delay) Google ignores, files over the 500 KiB limit, and BOM/duplicate/empty-rule issues. |
| [`schema-markup-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/schema-markup-audit) | Audit a website's structured data: extract JSON-LD, Microdata, and RDFa, validate against schema.org and Google rich result requirements, and find missing, invalid, or incomplete markup. |
| [`site-architecture-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/site-architecture-audit) | Audit a website's architecture: hostname and protocol canonicalization, robots.txt, XML sitemap parity, crawl and index directive conflicts, URL structure quality, click-depth distribution, and directory taxonomy. |
| [`sitemap-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/sitemap-audit) | Audit a website's XML sitemaps: discovers sitemaps from robots.txt, follows sitemap index files, and validates every listed URL for non-200 status, redirects, noindex/robots-blocked URLs, canonicalized-away URLs, wrong host/protocol, duplicates, oversized sitemaps (over 50,000 URLs or 50MB), parse errors, and lastmod/priority/changefreq hygiene. |
| [`soft-404-audit`](https://github.com/JakeLabate/Claude-SEO-Skills/tree/main/soft-404-audit) | Audit a website for soft 404s: error pages served with a 200 status, a server that returns 200 for every unknown URL, thin pages matching the site's error template, and empty/near-empty pages. |

## Install

Install all skills into your global Claude skills directory (`~/.claude/skills/`):

```bash
npx claude-seo-skills install
```

Other options:

```bash
# Install only specific skills
npx claude-seo-skills install sitemap-audit robots-txt-audit

# Install into the current project's ./.claude/skills instead of the global dir
npx claude-seo-skills install --project

# Install into a custom directory, overwriting anything already there
npx claude-seo-skills install --dir ~/my-skills --force

# List available skills
npx claude-seo-skills list
```

Or install the CLI globally:

```bash
npm install -g claude-seo-skills
claude-seo-skills install
```

## Manual usage

You can also copy a skill folder into your Claude skills directory (e.g., `~/.claude/skills/` for Claude Code) or upload it where skills are supported. Claude will invoke the skill automatically when a request matches its description.
