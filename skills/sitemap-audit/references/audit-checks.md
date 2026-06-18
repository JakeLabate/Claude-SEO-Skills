# Sitemap Audit Checks

Full definitions, thresholds, and rationale for each audit check.

The guiding principle: **an XML sitemap should list only final, canonical, indexable `200` URLs.** Most high-severity checks enforce that contract, because a sitemap full of redirects, errors, and noindexed URLs wastes crawl budget and erodes the trust search engines place in the file.

## High severity

### 1. No parseable sitemap found

- **Definition:** No sitemap was discovered via robots.txt or the common fallback paths, or every candidate failed to parse.
- **Why it matters:** Without a sitemap, search engines rely entirely on link discovery; new and deep pages are found slowly or not at all.
- **Fix:** Generate an XML sitemap of canonical indexable URLs and declare it in robots.txt.

### 2. Sitemap parse error / fetch error

- **Definition:** A sitemap file returned non-200 (fetch error) or is not valid XML / not a valid `urlset`/`sitemapindex` (parse error).
- **Why it matters:** A broken sitemap may be ignored entirely, taking all its URLs with it.
- **Fix:** Repair the XML (well-formed, correct namespace, valid encoding) and ensure the file returns 200 with an XML content type.

### 3. Sitemap exceeds 50,000 URLs

- **Definition:** A single `urlset` lists more than 50,000 URLs.
- **Why it matters:** The sitemaps protocol caps a single file at 50,000 URLs; anything beyond may be truncated or rejected.
- **Fix:** Split into multiple sitemaps under the limit and list them in a sitemap index.

### 4. Sitemap exceeds 50MB uncompressed

- **Definition:** A single sitemap file exceeds 50MB uncompressed.
- **Why it matters:** The protocol caps uncompressed size at 50MB; oversized files may be ignored.
- **Fix:** Split the sitemap and/or serve it gzipped, keeping each file under 50MB uncompressed.

### 5. Listed URL returns 4xx/5xx/error

- **Definition:** A URL in the sitemap returns a 4xx, 5xx, or connection error.
- **Why it matters:** Submitting dead URLs wastes crawl budget and signals a stale, low-quality sitemap.
- **Fix:** Remove the URL, or fix the page so it returns 200 if it should exist.

### 6. Listed URL redirects

- **Definition:** A sitemap URL returns a 3xx redirect instead of being a final 200.
- **Why it matters:** Sitemaps should contain destination URLs, not redirects. Redirecting entries waste a hop and suggest the sitemap was not regenerated after a move.
- **Fix:** Replace the URL with its final destination (or remove it if the destination is already listed).

### 7. Listed URL is noindex

- **Definition:** A sitemap URL is marked `noindex` (or `none`) via a meta robots tag or the `X-Robots-Tag` HTTP header.
- **Why it matters:** Including a page in the sitemap says "please index this", while `noindex` says the opposite — a direct conflict that confuses crawlers and wastes budget.
- **Fix:** Decide the page's fate. If it should be indexed, remove `noindex`; if not, remove it from the sitemap.

### 8. Listed URL is blocked by robots.txt

- **Definition:** A sitemap URL's path is disallowed for the `*` user-agent in robots.txt.
- **Why it matters:** Crawlers cannot fetch the page to honor the sitemap, and a blocked-but-submitted URL is a contradictory signal.
- **Fix:** Either unblock the path in robots.txt (if it should be crawled) or remove the URL from the sitemap.

## Medium severity

### 9. Listed URL canonicalizes to a different URL

- **Definition:** A sitemap URL returns 200 but its `rel="canonical"` points to a different URL.
- **Why it matters:** The sitemap is nominating a non-canonical URL; search engines will prefer the canonical and may distrust the sitemap.
- **Fix:** List the canonical URL in the sitemap instead of the variant.

### 10. Listed URL is on the wrong host or protocol

- **Definition:** A sitemap URL is on a different host (e.g., `www` vs. non-`www`, a different subdomain) or uses `http` when the site is `https`.
- **Why it matters:** Sitemaps should reference the canonical host and protocol; mismatches create redirects (see check 6) and split signals. Cross-domain URLs are also generally ignored unless cross-submission is configured.
- **Fix:** Rewrite all URLs to the canonical host and `https://`.

### 11. Sitemaps not declared in robots.txt

- **Definition:** Sitemaps exist but none are referenced by a `Sitemap:` directive in robots.txt.
- **Why it matters:** robots.txt is a primary discovery path; without it, search engines depend on manual submission alone.
- **Fix:** Add a `Sitemap:` line (absolute URL) to robots.txt for each sitemap, or for the sitemap index.

## Low severity

### 12. Duplicate URL across sitemaps

- **Definition:** The same URL appears in more than one sitemap file.
- **Why it matters:** Harmless but messy; usually indicates overlapping generation rules and inflates reported counts.
- **Fix:** Partition URLs so each appears in exactly one sitemap.

### 13. Missing / invalid / future lastmod

- **Definition:** A `<lastmod>` is absent, not a valid W3C datetime, or set in the future.
- **Why it matters:** Google uses `lastmod` as a recrawl hint only when it is consistent and trustworthy; missing or bogus values (e.g., every URL "modified today", or a future date) cause it to be ignored.
- **Fix:** Emit an accurate W3C datetime reflecting the real last content change. If you cannot maintain it accurately, omit it rather than faking it.

### 14. Invalid priority or changefreq

- **Definition:** `<priority>` outside `0.0`–`1.0`, or `<changefreq>` not one of the allowed values (`always`, `hourly`, `daily`, `weekly`, `monthly`, `yearly`, `never`).
- **Why it matters:** Invalid values are ignored. Note that Google ignores `priority` and `changefreq` entirely regardless of validity.
- **Fix:** Correct or, more simply, drop `priority`/`changefreq` — they add bytes without SEO benefit for Google.
