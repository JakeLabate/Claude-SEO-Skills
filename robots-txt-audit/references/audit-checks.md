# Robots.txt Audit Checks

Full definitions, thresholds, and rationale for each audit check.

The guiding principle: **robots.txt should return a small, valid `200` plain-text file from the site root that lets crawlers reach every page and resource you want indexed, declares your sitemap, and blocks only what you deliberately want kept out of the crawl.** Remember that robots.txt governs *crawling*, not *indexing* — a disallowed URL can still appear in search results without a snippet.

## High severity

### 1. robots.txt returns 5xx

- **Definition:** `/robots.txt` returns a 5xx server error.
- **Why it matters:** Google treats a persistent 5xx on robots.txt as "disallow everything" and will pause crawling of the whole site until it recovers. This can quietly drop a site out of the index.
- **Fix:** Make robots.txt return `200` (or `404`, which is read as "allow all"). Never let it 5xx; if the file is generated dynamically, add a static fallback.

### 2. robots.txt redirects

- **Definition:** `/robots.txt` returns a 3xx redirect instead of the file itself.
- **Why it matters:** Crawlers follow one redirect for robots.txt, but redirect chains, cross-host redirects, or redirects to an HTML page lead to the file being misread or ignored. Each host/subdomain/protocol should serve its own robots.txt.
- **Fix:** Serve robots.txt directly at `https://<host>/robots.txt` with a `200`, no redirect.

### 3. robots.txt served as HTML

- **Definition:** The response body is an HTML document (e.g., a soft-404 or a CMS page) rather than plain text.
- **Why it matters:** An HTML "file not found" page is not a valid robots.txt; rules are not parsed and discovery breaks. It often masks a misconfigured route.
- **Fix:** Serve real `text/plain` robots.txt content; return a genuine `404` if there is no file.

### 4. Sitewide `Disallow: /`

- **Definition:** A user-agent group contains `Disallow: /` with no `Allow:` re-opening the root.
- **Why it matters:** This blocks the entire site from crawling. When it targets `User-agent: *` it is the single most damaging robots.txt mistake — commonly left over from a staging environment and pushed to production.
- **Fix:** Remove the line, or scope the block to the specific paths you mean to exclude. Confirm intent before keeping any sitewide block on a live site.

### 5. Syntax error

- **Definition:** A line is malformed — missing the `field: value` colon, a `Disallow`/`Allow` appearing before any `User-agent`, or an empty `User-agent`/`Sitemap` value.
- **Why it matters:** Crawlers skip lines they cannot parse, so a typo can silently drop a rule or attach rules to the wrong group, producing crawl behavior you never intended.
- **Fix:** Correct each line to `field: value`, and make sure every `Disallow`/`Allow` follows a `User-agent` declaration.

### 6. File exceeds 500 KiB

- **Definition:** robots.txt is larger than 500 KiB.
- **Why it matters:** Google only parses the first 500 KiB; any rules past that point are ignored, which can unexpectedly expose or block paths.
- **Fix:** Trim the file — consolidate rules with wildcards (`*`, `$`) and remove dead entries so all directives fit under the limit.

## Medium severity

### 7. Render-critical resource blocked

- **Definition:** A CSS or JS file referenced by the homepage is disallowed for `User-agent: *`.
- **Why it matters:** Google renders pages before ranking them. Blocking the CSS/JS it needs can make pages look broken to the renderer, hurting mobile-friendliness and content evaluation.
- **Fix:** Add `Allow:` rules (or remove the `Disallow`) so the rendering resources are crawlable. Blocking truly private scripts is fine; blocking theme/app bundles is not.

### 8. No `Sitemap:` directive

- **Definition:** robots.txt contains no `Sitemap:` line.
- **Why it matters:** robots.txt is a primary sitemap-discovery path; without it, search engines rely on manual submission alone.
- **Fix:** Add an absolute `Sitemap:` line for each sitemap, or for the sitemap index.

### 9. Declared `Sitemap:` URL unreachable

- **Definition:** A `Sitemap:` value is not an absolute URL, or the absolute URL it points to returns non-200.
- **Why it matters:** A broken or relative sitemap reference cannot be fetched, defeating the purpose of declaring it. The `Sitemap:` directive must be a full absolute URL.
- **Fix:** Use an absolute `https://` URL and ensure the sitemap returns `200`.

### 10. No default `User-agent: *` group

- **Definition:** robots.txt has user-agent groups but none for `*`.
- **Why it matters:** A crawler uses only the most specific group that matches its name; with no `*` fallback, any agent you did not name gets no rules at all, which may be unintended.
- **Fix:** Add a `User-agent: *` group expressing the default crawl policy.

### 11. Unsupported directive

- **Definition:** A directive Google does not support appears in the file — most importantly `noindex` and `nofollow`, plus `crawl-delay`, `host`, `request-rate`, `clean-param`.
- **Why it matters:** These are silently ignored by Google. Relying on `noindex` in robots.txt to deindex a page does not work — the page stays indexable. `crawl-delay` gives a false sense of rate control.
- **Fix:** Remove them. Enforce `noindex`/`nofollow` via meta robots or `X-Robots-Tag` on crawlable pages; manage crawl rate in Search Console.

## Low severity

### 12. robots.txt missing entirely (404)

- **Definition:** `/robots.txt` returns 404 (or is unreachable).
- **Why it matters:** A 404 is valid and means "allow all", so this is not harmful. But a real file lets you declare the sitemap and document intended crawl policy in one place.
- **Fix:** Add a minimal robots.txt with a `Sitemap:` line and any intended rules.

### 13. Duplicate `User-agent: *` group

- **Definition:** More than one `User-agent: *` group exists.
- **Why it matters:** Rules may be merged or, in some parsers, only one group honored — making behavior ambiguous and hard to maintain.
- **Fix:** Consolidate all `*` rules into a single group.

### 14. UTF-8 BOM present

- **Definition:** A UTF-8 byte-order mark precedes the file.
- **Why it matters:** Most parsers tolerate a leading BOM, but some may misread the first directive. It is harmless to remove and safer without.
- **Fix:** Save robots.txt as UTF-8 without a BOM.

### 15. Empty `Disallow:` alongside real rules

- **Definition:** A group contains an empty `Disallow:` (which allows everything) together with non-empty `Disallow` rules.
- **Why it matters:** Usually a leftover or copy-paste artifact. It is a no-op next to real rules but signals the file may not say what the author thinks.
- **Fix:** Remove the empty line unless it is intentionally the only rule in a deliberately open group.
