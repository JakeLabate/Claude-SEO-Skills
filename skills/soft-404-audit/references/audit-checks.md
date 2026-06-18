# Soft 404 Audit Checks

Definitions and rationale. A **soft 404** is a page that returns HTTP `200 OK` but
is really a "not found", empty, or error page. Google flags these in Search
Console because they waste crawl budget and can get otherwise-fine URLs dropped;
users hit dead ends that look like real pages.

## High severity

### 1. Soft 404 (error page served as 200)
- **Definition:** A page returning HTTP 200 whose title or H1 contains a
  "not found" / error phrase ("404", "page not found", "no longer exists",
  "sorry, we couldn't find…", etc.).
- **Why it matters:** Search engines may index the error page, or (more often)
  distrust the site's status codes and drop real URLs. Users think the link works
  until they read the page.
- **Fix:** Return a real `404` (or `410` if permanently gone) status for missing
  content. If the URL *should* resolve, fix whatever makes it render the error.

### 2. Missing pages return 200
- **Definition:** A request to a deliberately non-existent URL returns `200`
  instead of `404`/`410` (detected via the missing-page probe).
- **Why it matters:** The whole site serves a soft 404 for every unknown URL, so
  typos, old links, and crawler guesses all become indexable 200 "pages". This is
  a server/router misconfiguration affecting the entire domain.
- **Fix:** Configure the server/framework to return `404` for unmatched routes and
  render the custom 404 page *with* a 404 status.

## Medium severity

### 3. Thin page matching the error template
- **Definition:** A 200 page that is very thin (few words) **and** matches the
  missing-page probe's fingerprint (same title, similarly empty) without an
  obvious error phrase.
- **Why it matters:** Strong sign the page is the site's error/empty template
  served under a real URL — a soft 404 that phrase-matching alone misses.
- **Fix:** Confirm the URL should exist; if not, return 404. If it should, ensure
  the real content renders server-side.

## Low severity

### 4. Empty / near-empty page
- **Definition:** A 200 page with almost no visible text and no error phrase.
- **Why it matters:** May be a legitimate page that renders content via JavaScript
  (which this crawler doesn't execute), a placeholder, or a thin page. Worth a
  human look, not necessarily a soft 404.
- **Fix:** If it's a placeholder, add content or noindex it; if it's
  JS-rendered, verify search engines can see the content. Cross-check the
  `content-quality-audit` skill.

## Notes

- This crawler does **not** execute JavaScript. A page that's empty in raw HTML
  but populated by a client-side framework will look thin here — verify before
  treating it as a soft 404.
- Tune `--thin-words` to the site; content-heavy sites may warrant a higher
  threshold than the default of 50.
