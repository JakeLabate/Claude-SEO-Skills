# External Link Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Broken external links

- **Definition:** An external `<a href>` whose target returns HTTP 4xx/5xx, or whose host cannot be resolved (link rot).
- **Why it matters:** Dead outbound links harm user experience and signal an unmaintained page; pages full of rot tend to lose trust and rankings.
- **Fix:** Replace with a live equivalent resource or an archived copy (e.g., Wayback Machine), or remove the link and keep the plain text.

### 2. Affiliate/paid links missing `rel="sponsored"`

- **Definition:** Links to known affiliate or paid-placement domains (or links with affiliate URL parameters such as `tag=`, `ref=`, `aff_id=`) that lack `rel="sponsored"` (or legacy `nofollow`).
- **Why it matters:** Google requires paid/affiliate links to be qualified; unflagged paid links risk manual link-scheme penalties.
- **Fix:** Add `rel="sponsored"` (optionally `sponsored nofollow`) to every paid or affiliate link.

## Medium severity

### 3. Insecure `http://` external links

- **Definition:** Outbound links using `http://` where the destination supports HTTPS.
- **Why it matters:** Sends users through an insecure hop, leaks referrer data, and often produces an extra redirect.
- **Fix:** Update the link to the `https://` URL. If the destination has no HTTPS, consider whether to keep the link at all.

### 4. Redirected external links

- **Definition:** An external link whose target returns 3xx.
- **Threshold:** Flag all 3xx targets; treat chains of 2+ hops and redirects to a different domain as higher priority (the destination content may have changed).
- **Fix:** Update links to point directly to the final destination URL after verifying it still matches the intended content.

### 5. `target="_blank"` without `rel="noopener"`/`noreferrer`

- **Definition:** External links opening a new tab without `rel="noopener"` or `rel="noreferrer"`.
- **Why it matters:** Legacy browsers expose `window.opener` to the destination page (reverse tabnabbing); it can also hurt performance.
- **Fix:** Add `rel="noopener"` (modern browsers imply it, but explicit is safest for older browsers).

### 6. User-generated content links missing `rel="ugc"`/`nofollow`

- **Definition:** External links inside comments, forums, or other user-submitted areas without `rel="ugc"` or `rel="nofollow"`.
- **Detection:** Ask the user which page sections accept user-generated content if unclear.
- **Why it matters:** Unqualified UGC links pass equity to spam targets and invite comment spam.
- **Fix:** Add `rel="ugc"` (or `nofollow`) to all links in user-submitted content, ideally via the platform template.

## Low severity

### 7. Generic anchor text on external links

- **Definition:** External links whose anchor text is non-descriptive.
- **Detection list:** "click here", "here", "read more", "learn more", "more", "this page", "link", "source", bare URLs, empty anchors (image links without `alt` text).
- **Fix:** Use descriptive anchor text that tells users and crawlers what the destination is.

### 8. Excessive external links

- **Definition:** Pages with more than ~100 outgoing external links.
- **Why it matters:** Can look like a link farm or directory, dilutes the value of each citation, and overwhelms readers.
- **Fix:** Trim to the most valuable references; split genuine resource lists into curated, focused pages.

### 9. Sitewide external links

- **Definition:** The same external link appearing in `<nav>` or `<footer>` across most pages (e.g., "designed by", widget credits, badge links).
- **Why it matters:** Sitewide followed outbound links are a classic spam pattern and leak equity from every page.
- **Fix:** Keep only deliberate sitewide links; add `rel="nofollow"`/`sponsored` to credit or reciprocal links, or move them to a single about/credits page.

## Additional signals to note (informational)

- **Domain concentration** — if a large share of external links point to one domain, confirm it's intentional (not injected spam).
- **Suspicious destinations** — links to parked domains, expired-domain redirects, gambling/pharma/adult sites the user didn't intend to cite; flag for manual review as possible hacked-content injection.
- **Tracking-parameter bloat** — outbound URLs carrying long tracking query strings (`utm_*`, `fbclid`); link the clean canonical URL where practical.
- **Linking to competitors with keyword-rich anchors** — note for the user to confirm it's intentional.
