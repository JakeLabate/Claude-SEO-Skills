# Site Architecture Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Multiple indexable hostname/protocol variants

- **Definition:** The site answers with HTTP 200 on more than one of the four host/protocol variants (`http://`, `https://`, with and without `www`) instead of redirecting every variant to one canonical version with a 301.
- **Why it matters:** Each resolvable variant is a separate, fully duplicated copy of the site. It splits link equity, wastes crawl budget, and forces search engines to guess the canonical host.
- **Fix:** Pick one canonical host (almost always `https://` and a single `www`/non-`www` choice) and 301-redirect the other three variants to it. Confirm the canonical tag and internal links use the chosen host.

### 2. Important pages blocked by robots.txt

- **Definition:** A `Disallow` rule in robots.txt matches URLs that are linked from the site and otherwise indexable (200, not noindex).
- **Why it matters:** Disallowed URLs are not crawled, so their content and links are never seen. If they are also linked elsewhere they can still appear in results as bare URLs with no snippet.
- **Fix:** Narrow or remove the `Disallow`. Reserve robots.txt for genuinely crawl-wasteful spaces (internal search, faceted parameter URLs); use `noindex` (not `Disallow`) for pages that should be crawlable but kept out of the index.

### 3. Conflicting crawl/index directives

- **Definition:** Two signals on the same URL contradict each other. Common cases:
  - A URL is `Disallow`ed in robots.txt **and** carries a `noindex` meta tag. The crawler cannot fetch the page, so it never sees the `noindex`, and the URL can linger in the index.
  - A page is `noindex` **and** has a canonical pointing to a different URL. Canonical asks to consolidate; noindex asks to drop. Search engines may ignore both.
  - A page's canonical points to a URL that is non-200, redirects, or is itself `noindex`.
- **Why it matters:** Contradictory directives produce unpredictable indexing and waste the signals entirely.
- **Fix:** Choose one outcome per URL. To deindex but keep crawlable, use `noindex` and allow crawling. To consolidate duplicates, use a self-consistent canonical that points to a live, indexable, self-canonical target.

### 4. Sitemap lists non-indexable URLs

- **Definition:** The XML sitemap contains URLs that are non-200, redirect (3xx), carry `noindex`, or canonicalize to a different URL.
- **Why it matters:** XML sitemaps are a statement of the canonical, indexable URL set. Polluting them with redirects, errors, or non-canonical URLs erodes trust in the sitemap and wastes crawl budget on dead ends.
- **Fix:** Regenerate the sitemap to include only final, 200, self-canonical, indexable URLs. Automate generation from the canonical URL set rather than maintaining it by hand.

## Medium severity

### 5. Indexable pages missing from the XML sitemap

- **Definition:** Pages that are 200, not `noindex`, and self-canonical, but absent from every sitemap.
- **Why it matters:** Sitemaps speed discovery and give search engines a complete picture of the canonical URL set. Gaps slow indexing of new or deep content.
- **Fix:** Add the missing indexable URLs to the sitemap. If the gap is large and systematic (a whole section missing), fix the sitemap generator rather than patching URLs individually.

### 6. Excessive click depth or top-heavy depth distribution

- **Definition:** Pages requiring more than 3 clicks from the homepage to reach, or a distribution where a large share of pages sit beyond depth 3.
- **Threshold:** Flag click depth greater than `--max-click-depth` (default 3); depth greater than 5 is critical. Also flag when more than ~40% of crawled pages sit beyond the threshold.
- **Why it matters:** Depth is a proxy for importance and for crawl reachability. Deep pages are crawled less often and accrue less internal equity.
- **Fix:** Flatten the architecture with hub/category pages, contextual links from shallow high-authority pages, and a navigation that exposes key sections within two or three clicks.

### 7. URL structure problems

- **Definition:** URLs that are hard to read, crawl, or maintain. Detected sub-cases:
  - Uppercase letters in the path (case-sensitivity duplicate risk)
  - Underscores as word separators (hyphens are the convention)
  - Spaces or percent-encoded characters in the path
  - Over-long URLs (path + query beyond ~115 characters)
  - Over-deep paths (more than `--max-url-depth` path segments, default 4)
  - ID-only or opaque slugs (final segment is all digits or a long random token, carrying no keyword signal)
- **Why it matters:** Clean, lowercase, hyphenated, shallow, descriptive URLs are easier to crawl, share, and understand, and they reduce duplicate-content risk from case or encoding variants.
- **Fix:** Adopt a lowercase, hyphenated, descriptive URL convention; 301 the old URLs to the new ones. Apply at the template level so new URLs are correct by default.

### 8. Inconsistent URL forms in internal links

- **Definition:** The same site is linked using inconsistent URL forms. Detected sub-cases across the internal links found:
  - Mixed trailing slash (both `/path` and `/path/` linked)
  - Mixed protocol (some internal links use `http://` on an `https://` site)
  - Mixed host (some links use `www`, others non-`www`)
- **Why it matters:** Each inconsistent form is a redirect hop at best and a duplicate URL at worst. It dilutes equity and muddies canonicalization.
- **Fix:** Standardize internal links on one form (canonical host, one trailing-slash convention) and enforce it in templates. Make sure server redirects normalize the other forms.

### 9. Crawlable parameter URLs

- **Definition:** Internal links or crawled URLs carrying query strings that create duplicate or near-duplicate crawl spaces. Categorized as:
  - Tracking parameters in internal links (`utm_*`, `gclid`, `fbclid`)
  - Session identifiers (`sid`, `sessionid`, `phpsessid`)
  - Sort/filter/pagination parameters that multiply URLs
- **Why it matters:** Parameterized duplicates waste crawl budget and split signals. Tracking parameters never belong on internal links.
- **Fix:** Link to clean canonical URLs internally (strip tracking params). For functional parameters, set self-referencing canonicals to the clean URL, and where appropriate disallow the parameter space in robots.txt.

### 10. Missing or non-200 robots.txt

- **Definition:** `/robots.txt` is absent or returns a non-200 status.
- **Why it matters:** A missing robots.txt is not fatal (everything is allowed by default), but a 5xx robots.txt can cause search engines to pause crawling entirely, and the absence means no place to declare sitemaps or manage crawl-wasteful spaces.
- **Fix:** Serve a valid `200` robots.txt, even a permissive one, and reference the sitemap from it.

### 11. No XML sitemap found

- **Definition:** No sitemap at `/sitemap.xml` and none declared in robots.txt.
- **Why it matters:** Sitemaps are the most direct discovery channel, especially for large sites, new content, and deep pages.
- **Fix:** Generate an XML sitemap of canonical indexable URLs and declare it in robots.txt and Search Console.

## Low severity

### 12. Pages missing a self-referencing canonical

- **Definition:** Indexable 200 pages with no `rel="canonical"` at all.
- **Why it matters:** A self-referencing canonical is a low-cost defense against parameter and variant duplication. Its absence is not an error but leaves the page exposed.
- **Fix:** Add a self-referencing canonical to every indexable page at the template level.

### 13. Sitemap not referenced in robots.txt

- **Definition:** A sitemap exists but is not declared with a `Sitemap:` line in robots.txt.
- **Why it matters:** The robots.txt `Sitemap:` directive is a standard discovery path for every crawler.
- **Fix:** Add `Sitemap: https://example.com/sitemap.xml` to robots.txt.

### 14. Thin or inconsistent directory taxonomy

- **Definition:** First-level directories (sections) that contain only a single page, or a taxonomy where naming conventions are inconsistent across sections.
- **Why it matters:** Single-page sections suggest a hierarchy that does not reflect real content groupings; inconsistent naming makes the architecture harder to reason about and scale.
- **Fix:** Consolidate one-off sections into a relevant parent, or expand them into genuine hubs. Standardize directory naming.

### 15. Sitemap over size limits without a sitemap index

- **Definition:** A single sitemap file with more than 50,000 URLs or larger than 50 MB uncompressed, with no sitemap index splitting it.
- **Why it matters:** Over-limit sitemaps may be rejected or partially processed.
- **Fix:** Split into multiple sitemaps under the limits and reference them from a sitemap index file.

## Additional signals to note (informational)

- **Subdomain sprawl** : content split across many subdomains (`blog.`, `shop.`, `help.`). Confirm it is intentional; subfolders usually consolidate authority better than subdomains.
- **hreflang presence** : for international sites, note whether `hreflang` annotations exist and appear reciprocal. Full hreflang validation is out of scope here.
- **Breadcrumb wayfinding** : deep pages without breadcrumb navigation are harder to place in the hierarchy (overlaps `schema-markup-audit` for `BreadcrumbList`).
- **Crawl vs sitemap count delta** : a large gap between crawlable pages and sitemap URL count, in either direction, is worth explaining.
- **Mixed content** : `https://` pages linking `http://` internal resources.
