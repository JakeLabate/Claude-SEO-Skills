# Canonical Tag Audit Checks

Full definitions, thresholds, and rationale for each check. A `rel="canonical"`
tells search engines which URL is the authoritative version of a page; getting it
wrong silently removes pages from the index or splits ranking signals.

## High severity

### 1. Missing canonical
- **Definition:** An indexable (`200`, non-noindex) HTML page with no
  `<link rel="canonical">` and no `Link: rel="canonical"` header.
- **Why it matters:** Without a canonical, parameterized, syndicated, or
  duplicated variants of the page compete and split signals; the engine picks a
  canonical for you, sometimes the wrong one.
- **Fix:** Add a self-referencing absolute canonical to every indexable page.

### 2. Multiple conflicting canonicals
- **Definition:** A page with more than one distinct canonical URL (across `<link>`
  tags and/or the HTTP header).
- **Why it matters:** Conflicting canonicals are ambiguous; Google ignores them
  all and falls back to its own choice.
- **Fix:** Emit exactly one canonical. Usually a CMS theme plus an SEO plugin both
  inject one — remove the duplicate.

### 3. Canonical points to a non-200 URL
- **Definition:** The canonical target returns 4xx/5xx or fails to load.
- **Why it matters:** Canonicalizing to a dead URL tells the engine the real page
  doesn't exist; the page may be dropped from the index.
- **Fix:** Point the canonical at a live `200` URL (usually the page itself).

### 4. Canonical points to a redirect
- **Definition:** The canonical target 3xx-redirects to another URL.
- **Why it matters:** A canonical should name the final destination, not a hop.
  Chained canonical→redirect signals dilute and confuse consolidation.
- **Fix:** Set the canonical to the redirect's final destination URL.

## Medium severity

### 5. Canonical points to a noindex URL
- **Definition:** The canonical target carries `noindex` (meta or `X-Robots-Tag`).
- **Why it matters:** You're consolidating signals onto a page you've told the
  engine not to index — contradictory; both URLs can end up dropped.
- **Fix:** Canonicalize to an indexable URL, or remove the noindex from the target.

### 6. Relative canonical
- **Definition:** The canonical `href` is a relative path rather than an absolute
  URL.
- **Why it matters:** Relative canonicals are resolved against the current URL and
  break under parameters, alternate hosts, or proxying.
- **Fix:** Always emit a fully-qualified absolute URL (`https://host/path`).

### 7. Cross-host canonical
- **Definition:** The canonical points to a different host than the page.
- **Why it matters:** Sometimes intentional (syndication), but usually a
  misconfiguration that hands ranking to the wrong domain or a staging host.
- **Fix:** Confirm it's deliberate; otherwise canonicalize within the live host.

### 8. Protocol downgrade in canonical
- **Definition:** An `https://` page canonicalizes to an `http://` URL.
- **Why it matters:** Points the authoritative version at the insecure URL,
  undermining the HTTPS migration.
- **Fix:** Use `https://` in the canonical.

### 9. Header / HTML canonical conflict
- **Definition:** The `Link: rel="canonical"` header and the in-page canonical
  disagree.
- **Why it matters:** Same ambiguity as multiple canonicals; the engine may honor
  either.
- **Fix:** Make them identical, or emit only one.

## Low severity

### 10. Canonical contains a fragment
- **Definition:** The canonical URL includes a `#fragment`.
- **Why it matters:** Fragments are ignored for indexing and usually indicate a
  templating bug.
- **Fix:** Drop the fragment from the canonical.

## Informational (note, not counted as an issue)

- **Non-self canonical** — the page canonicalizes to a *different* URL. This is
  legitimate and common (parameter variants, print pages, syndicated copies). It
  is reported so you can confirm each one is intentional and that the target is
  the right consolidation point — not because it is inherently wrong.
