# Internal Link Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Broken internal links

- **Definition:** An internal `<a href>` whose target returns HTTP 4xx or 5xx.
- **Why it matters:** Wastes crawl budget, loses link equity, and harms user experience.
- **Fix:** Update the link to the correct live URL, or remove it. If the target was intentionally removed, 301-redirect it to the closest relevant page.

### 2. Orphan pages

- **Definition:** A page present in the sitemap (or known page set) that receives zero inbound internal links from crawlable pages.
- **Why it matters:** Search engines may never discover the page through crawling; it receives no internal link equity.
- **Fix:** Add at least 2–3 contextual internal links from topically related pages. Important pages should also be reachable from navigation or hub pages.

## Medium severity

### 3. Redirected internal links and redirect chains

- **Definition:** An internal link whose target returns 3xx. A chain is two or more consecutive redirects.
- **Threshold:** Flag all 3xx targets; treat chains of 2+ hops as higher priority.
- **Fix:** Update links to point directly to the final destination URL.

### 4. Deep pages (click depth)

- **Definition:** Pages requiring more than 3 clicks from the homepage to reach.
- **Threshold:** Depth > 3 flagged; depth > 5 is critical.
- **Fix:** Link to deep pages from hub/category pages, the homepage, or popular high-depth-0/1 pages.

### 5. Generic or weak anchor text

- **Definition:** Internal links whose anchor text is non-descriptive.
- **Detection list:** "click here", "here", "read more", "learn more", "more", "this page", "link", bare URLs, empty anchors (image links without `alt` text).
- **Fix:** Use descriptive anchor text that includes the target page's primary topic or keyword. Avoid exact-match repetition across many links; vary naturally.

### 6. Links to non-canonical or noindexed URLs

- **Definition:** Internal links pointing to a URL whose canonical tag points elsewhere, or whose meta robots is `noindex`.
- **Why it matters:** Sends crawlers and equity to pages that won't be indexed.
- **Fix:** Point links at the canonical, indexable URL.

### 7. Under-linked important pages

- **Definition:** High-value pages (conversion pages, key content) with fewer inbound internal links than the site median.
- **Detection:** Compare inbound link counts; ask the user which pages are priorities if unclear.
- **Fix:** Add contextual links from related, well-linked pages with descriptive anchors.

## Low severity

### 8. Excessive outgoing links

- **Definition:** Pages with more than ~150 outgoing internal links.
- **Why it matters:** Dilutes equity per link and can indicate poor information architecture.
- **Fix:** Trim navigation bloat; split mega-pages into focused hub pages.

### 9. Nofollow on internal links

- **Definition:** Internal links carrying `rel="nofollow"` (or `sponsored`/`ugc`).
- **Why it matters:** Internal nofollow blocks equity flow and discovery with no benefit.
- **Fix:** Remove `nofollow` from internal links unless there is a deliberate reason (e.g., faceted URLs you want left uncrawled — prefer robots.txt for that).

## Additional signals to note (informational)

- Self-referencing links (page linking to itself) — usually harmless, note only.
- Duplicate links (same source → same target multiple times) — only the first anchor typically counts; consolidate where practical.
- Links using URL parameters or fragments that resolve to the same page — normalize to clean URLs.
- HTTP links on an HTTPS site — update to HTTPS.
