# Content Quality Audit Checks

Definitions, thresholds, and rationale. These checks flag pages that are unlikely
to rank or add value because they are too thin, duplicated, or buried under
markup. They are signals for human review, not verdicts — "thin" depends on
intent (a contact page is meant to be short).

## High severity

### 1. Thin content
- **Definition:** An indexable page with a visible word count well below the
  threshold (default 300).
- **Why it matters:** Pages with little unique content rarely satisfy a query and
  can drag down site-wide quality signals when there are many of them.
- **Fix:** Expand with genuinely useful content, consolidate several thin pages
  into one strong page, or `noindex` pages that exist for non-search reasons.
- **Caveat:** This crawler doesn't run JavaScript — a page populated client-side
  will look thin. Verify before acting.

### 2. Duplicate content
- **Definition:** Two or more indexable pages whose visible body text is
  identical (same normalized content hash).
- **Why it matters:** Duplicates compete with each other and split signals; search
  engines pick one and may ignore the rest.
- **Fix:** Canonicalize the duplicates to one URL, consolidate them, or
  differentiate the content. (Cross-check the `canonical-tag-audit` skill.)

## Medium severity

### 3. Near-duplicate content
- **Definition:** Two pages whose MinHash similarity exceeds the threshold
  (default 0.85) — nearly the same text, e.g. templated pages where only a name or
  city changes.
- **Why it matters:** Doorway-style near-duplicates add little unique value and can
  be treated as duplicates.
- **Fix:** Add substantial unique content per page, or consolidate the set behind
  one canonical.

### 4. Low text-to-HTML ratio
- **Definition:** Visible text is a very small fraction (default < 10%) of the raw
  HTML.
- **Why it matters:** Often a sign of heavy templating/boilerplate with little real
  content, or a JS-driven page with minimal server-rendered text.
- **Fix:** Increase the proportion of real content, trim bloated markup, or verify
  server-side rendering of the main content.

## Low severity

### 5. Missing H1
- **Definition:** An indexable page with no `<h1>`.
- **Why it matters:** The H1 frames the page topic for users and assistive tech and
  reinforces relevance. (For full heading analysis, use the
  `heading-structure-audit` skill.)
- **Fix:** Add a single descriptive H1 reflecting the page's primary topic.

## Notes

- **Tune the thresholds to the site.** A documentation site and a news site have
  very different "normal" word counts; pass `--thin-words` and `--similarity`
  accordingly. The summary reports the median word count to help calibrate.
- **JavaScript rendering** is the most common false positive across these checks —
  always confirm a flagged page isn't simply rendered client-side.
