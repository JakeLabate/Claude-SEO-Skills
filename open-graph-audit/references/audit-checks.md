# Open Graph / Twitter Card Audit Checks

Definitions, thresholds, and rationale. Open Graph (`og:*`) and Twitter Card
(`twitter:*`) tags control how a page looks when shared on social platforms and in
messaging apps. They don't directly affect rankings, but they drive click-through
and referral traffic, and broken share images make links look untrustworthy.

## High severity

### 1. Missing og:title
- **Definition:** Indexable page with no `og:title`.
- **Why it matters:** Platforms fall back to the `<title>` or a guess; the share
  card often shows truncated or wrong text.
- **Fix:** Add `og:title` (can mirror or improve on the page title; up to ~90 chars).

### 2. Missing og:image
- **Definition:** Indexable page with no `og:image` (or `og:image:secure_url`).
- **Why it matters:** Shares render as a bare text link with no thumbnail, sharply
  reducing engagement.
- **Fix:** Add an absolute `https://` `og:image` (recommended 1200×630).

### 3. Broken og:image
- **Definition:** The `og:image` URL returns a non-200 status.
- **Why it matters:** The share preview shows no image at all — worse than a
  missing tag because it looks broken.
- **Fix:** Point at a live image URL; verify it returns `200`.

## Medium severity

### 4. Missing og:description
- **Definition:** No `og:description`.
- **Fix:** Add a concise description (the meta description is a fine source).

### 5. Missing og:url
- **Definition:** No `og:url`.
- **Why it matters:** `og:url` is the canonical URL for sharing; without it,
  engagement can split across tracking-parameter variants of the URL.
- **Fix:** Set `og:url` to the page's canonical absolute URL.

### 6. og:url mismatch
- **Definition:** `og:url` differs from the page's canonical (or final) URL.
- **Why it matters:** Splits social signals or points shares at the wrong URL.
- **Fix:** Make `og:url` equal the canonical URL.

### 7. og:image not an image / relative
- **Definition:** The `og:image` content-type isn't `image/*`, or the URL is
  relative rather than absolute.
- **Why it matters:** Most platforms require an absolute URL and a real image;
  relative or non-image values are ignored.
- **Fix:** Use an absolute `https://` URL to a real image file.

## Low severity

### 8. Missing twitter:card
- **Definition:** No `twitter:card` and no OG tags to fall back on.
- **Why it matters:** Twitter/X can use OG as a fallback, but with neither, links
  render plain. (If OG is present, this is informational.)
- **Fix:** Add `twitter:card` (`summary_large_image` for most content).

### 9. og:title / og:description too long
- **Definition:** `og:title` over ~90 chars or `og:description` over ~300 chars.
- **Why it matters:** Platforms truncate; the cut-off point may drop the key
  message.
- **Fix:** Trim to fit.

## Informational (note, not counted as an issue)

- **Duplicate og:image across many pages** — one share image reused on 5+ pages.
  Fine for a brand default, but section- or page-specific images earn more
  engagement. Listed so you can decide.
