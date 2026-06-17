# Redirect Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Redirect loop

- **Definition:** The chain returns to a URL it has already visited (A → B → A, or a URL redirecting to itself).
- **Why it matters:** The page never resolves. Browsers show "too many redirects", and crawlers abandon the URL, so it cannot rank or pass equity.
- **Fix:** Find the two rules in conflict — most loops come from a pair of competing normalizations (trailing slash vs. no slash, www vs. non-www, HTTP vs. HTTPS, lowercase vs. mixed case). Keep one canonical form and make the other redirect to it exactly once.

### 2. Redirect chain ends in a 4xx/5xx/error

- **Definition:** A URL that redirects, but whose final destination returns 4xx, 5xx, or a connection error (status 0).
- **Why it matters:** The redirect actively sends users and crawlers to a dead end, wasting the link equity the redirect was meant to preserve.
- **Fix:** Repoint the redirect to a live, topically relevant page. Avoid defaulting everything to the homepage ("soft 404" behavior); map each old URL to its closest current equivalent.

### 3. Chain exceeds the hop limit

- **Definition:** The resolver hit its `--max-hops` ceiling without reaching a final status.
- **Why it matters:** Either an extremely long chain or an undetected loop; in both cases the destination is effectively unreachable for crawlers, which cap redirect following.
- **Fix:** Trace the chain manually, find where it fails to terminate, and replace it with a single direct 301.

### 4. Chain longer than allowed

- **Definition:** More redirect hops than `--max-chain` (default 1). Every redirect should reach its destination in one hop.
- **Why it matters:** Each hop adds latency and dilutes/risks the signals passed along. Google follows a limited number of hops and may stop consolidating signals on long chains.
- **Fix:** Update the redirect rules so the original URL points straight to the final destination (`A → B → C` becomes `A → C`). Keep the intermediate rules only if those intermediate URLs are themselves still requested directly.

### 5. HTTPS → HTTP downgrade

- **Definition:** A hop redirects from an `https://` URL to an `http://` URL.
- **Why it matters:** Downgrades break the secure chain, trigger browser warnings, and can strip security; on a migrated site it usually signals a misordered rule (the HTTPS redirect runs before the canonicalization).
- **Fix:** Reorder rules so HTTPS is enforced last (or first and consistently), ensuring no hop ever lands on `http://`.

## Medium severity

### 6. Temporary redirect for a permanent move

- **Definition:** A 302, 303, or 307 used where the move is permanent.
- **Why it matters:** Temporary redirects tell search engines to keep indexing the *old* URL and may not consolidate signals to the new one as reliably as a 301/308.
- **Fix:** Change to 301 (or 308 to preserve the request method). Reserve 302/307 for genuinely temporary situations: A/B tests, geolocation, maintenance pages, and cart/login flows.

### 7. Meta-refresh or JavaScript redirect

- **Definition:** The final document redirects via `<meta http-equiv="refresh">` or a client-side `location` assignment instead of an HTTP status redirect.
- **Why it matters:** Client-side redirects are slower, depend on rendering, and are interpreted inconsistently by crawlers. A `0`-second meta refresh is treated like a 301 by Google but is still discouraged; delayed refreshes are treated as soft 404s.
- **Fix:** Replace with a server-side 301.

### 8. Mixed permanent and temporary codes in one chain

- **Definition:** A single chain contains both a permanent (301/308) and a temporary (302/303/307) code.
- **Why it matters:** Inconsistent signals about whether the move is permanent; the temporary hop can prevent full consolidation even if the chain also contains a 301.
- **Fix:** Make every hop in the chain permanent (and collapse the chain to one hop while you are there).

### 9. Canonical points at a redirecting URL

- **Definition:** A page returns 200 but its `rel="canonical"` points to a URL that itself redirects.
- **Why it matters:** Canonicals should always point to the final, indexable 200 URL. Pointing at a redirect forces another hop and weakens the canonical signal.
- **Fix:** Update the canonical to the redirect's final destination.

## Low severity

### 10. Redirect drops the query string

- **Definition:** The requested URL carried a query string, and the final URL has none.
- **Why it matters:** Dropping parameters can lose tracking, pagination, filtering, or campaign attribution. Sometimes intentional (stripping junk params), sometimes a bug.
- **Fix:** Confirm intent. Preserve meaningful parameters through the redirect; strip only known-noise parameters deliberately.

### 11. Final page's canonical differs from its own URL

- **Definition:** A 200 page's canonical points somewhere other than its own final URL, and that target was not itself observed in the crawl.
- **Why it matters:** May be a legitimate cross-page canonical, or a sign the page is canonicalizing to a URL that no longer resolves. Worth a manual check.
- **Fix:** Verify the canonical target is a live 200 page and is the intended canonical; correct it if not.

## Notes

- Run with `--max-chain 0` against a sitemap or a list of canonical URLs to assert that every "indexable" URL is a direct 200 with no redirect at all.
- For migrations, feed the list of *old* URLs via `--url-list` so each legacy URL is verified to reach its new home in a single 301.
