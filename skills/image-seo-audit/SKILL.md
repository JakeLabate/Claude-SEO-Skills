---
name: image-seo-audit
description: Audit a website's images for SEO and Core Web Vitals. Crawls pages to find images with missing or empty alt text, missing width/height (layout shift), no lazy loading, oversized files, legacy formats (no WebP/AVIF), generic filenames, and broken image URLs. Use when the user asks to audit, analyze, check, or improve image SEO, alt text, image accessibility, image file sizes, image formats, or image loading performance of a website.
---

# Image SEO Audit

Audit the images of a website and produce an actionable SEO and performance report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze the images on a website for SEO or accessibility
- Find images with missing, empty, or poor `alt` text
- Find images that cause layout shift (missing `width`/`height`) or load slowly (no lazy loading, oversized files)
- Identify images served in legacy formats instead of WebP/AVIF
- Find broken images or generic, uninformative filenames

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, a list of URLs, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/blog/`), or a list of URLs.
3. **Crawl limits** — max pages (default 500) for live crawls.
4. **File checks** — whether to fetch each image to measure byte size and detect broken images (the `--check-files` flag; slower but enables the oversized-file and broken-image checks).
5. **Size budget** — the byte threshold above which an image is "oversized" (default 200 KB).

## Workflow

### Step 1: Gather the page set and extract images

- If a sitemap is available (`/sitemap.xml`), it is used to get the canonical page list.
- Otherwise, the crawler starts from the homepage following only same-host links.
- For local HTML folders, all `.html` files are enumerated.

Use `scripts/extract_images.py` to build an image inventory:

```bash
python3 scripts/extract_images.py https://example.com --max-pages 500 --check-files --output image_inventory.json
```

For every `<img>` the inventory records: absolute `src`, `alt` (null if the attribute is absent vs. empty string if `alt=""`), `width`/`height` attributes, `loading`, whether it has a `srcset`, whether it sits inside a `<picture>`, and its position in the page. With `--check-files`, each unique image URL is HEAD-requested to record HTTP status, content type, and byte size.

### Step 2: Run the audit checks

Use `scripts/audit_images.py` to run all audit checks against the inventory:

```bash
python3 scripts/audit_images.py image_inventory.json --max-bytes 200000 --output audit_report.json
```

The oversized-file and broken-image checks only run if the inventory was built with `--check-files`.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Missing `alt` attribute | High |
| Broken image (non-200 URL) | High |
| Missing `width`/`height` (layout shift) | Medium |
| Oversized file (> size budget) | Medium |
| Not lazy-loaded (below the fold) | Low |
| Legacy format with no modern `<picture>` source | Low |
| Generic filename | Low |
| Alt text too long (> 125 chars) | Low |
| Redundant alt prefix ("image of…") | Low |
| Empty `alt=""` (decorative — confirm intent) | Informational |
| Duplicate alt reused across many images | Informational |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages crawled, images found, alt-text coverage %, issue counts by severity
2. **Issues** — one section per failing check, listing the page, the image, and a specific fix
3. **Prioritized action list** — ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation. When drafting alt text:

- Describe what the image shows and its purpose on the page, in roughly 5–15 words
- Never start with "image of" or "picture of" — screen readers already announce it as an image
- Use `alt=""` only for purely decorative images; never invent details not visible in the image
- For dimensions, recommend the exact `width`/`height` attributes (or CSS `aspect-ratio`) that match the rendered size
- For oversized or legacy images, recommend compressing and serving WebP/AVIF via `<picture>` with a fallback

Example recommendations:

- Add alt text to the hero image on `/`: `alt="Team of nurses reviewing a patient chart at a bedside"`
- Add `width` and `height` to the 6 product thumbnails on `/shop` to stop layout shift
- Convert `/images/hero.png` (1.4 MB) to WebP and serve it through `<picture>`; this image loads on every page

## Optional: export the report as a Word document

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `references/audit-checks.md` — full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/extract_images.py` — crawl a site and build the image inventory (add `--check-files` for size/format checks)
- `scripts/audit_images.py` — run audit checks against an image inventory JSON file
