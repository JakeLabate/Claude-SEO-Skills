# Pagination Audit Checks

Definitions and rationale. Paginated series (blog listings, category pages,
search results) are easy to misconfigure in ways that hide content from search
engines. Google's current guidance: **each page in a series should be a
self-canonical, indexable URL**; `rel="next"`/`rel="prev"` are no longer used for
indexing (but aren't harmful).

## High severity

### 1. Paginated page canonicalizes to page 1
- **Definition:** A component page (page 2, 3, …) has a `rel="canonical"` pointing
  at page 1 of the series.
- **Why it matters:** This tells Google page 2+ is a duplicate of page 1, so the
  items and links that *only* appear on later pages are dropped from the index.
  This is the single most damaging pagination mistake.
- **Fix:** Make each paginated page self-canonical (`canonical` = its own URL).

## Medium severity

### 2. Paginated page is noindexed
- **Definition:** A component page (page 2+) carries `noindex`.
- **Why it matters:** `noindex` on paginated pages eventually drops them *and*
  causes Google to crawl their outgoing links less — deep items lose discovery.
- **Fix:** Let component pages be indexable, or ensure deep items are reachable by
  another path (e.g. the XML sitemap).

### 3. Paginated page missing a self-canonical
- **Definition:** A page 2+ has no canonical at all.
- **Why it matters:** Parameter and ordering variants of the listing can be
  treated as separate duplicate URLs.
- **Fix:** Add a self-referencing canonical to every paginated page.

### 4. Broken rel=next/prev target
- **Definition:** A `rel="next"`/`rel="prev"` points at a URL that is non-200 or
  redirects.
- **Why it matters:** Signals a stale or off-by-one pagination template and
  confuses any consumer still reading these hints.
- **Fix:** Point them at the correct live URLs, or remove them.

## Low severity

### 5. Inconsistent rel=next/prev reciprocity
- **Definition:** Page A's `next` is B, but B's `prev` is not A.
- **Fix:** Make the chain reciprocal, or drop `rel=next/prev` entirely.

### 6. First page carries a redundant page parameter
- **Definition:** The first page is served at `?page=1` (or `/page/1`) instead of
  the bare URL.
- **Why it matters:** Creates a duplicate of the canonical listing URL.
- **Fix:** Serve page 1 at the bare URL and 301 `?page=1` to it.

## Informational (note, not counted as an issue)

- **rel=next/prev present** — Google announced in 2019 it no longer uses these for
  indexing. They are not harmful and other engines may use them, so keeping them
  is fine; just don't rely on them to consolidate a series. Reported so you know
  they exist and aren't a substitute for the canonical/indexability fixes above.
