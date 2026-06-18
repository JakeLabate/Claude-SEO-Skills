# Mixed Content / HTTPS Audit Checks

Definitions and rationale. "Mixed content" is an insecure (`http://`) resource
loaded by a secure (`https://`) page. Browsers block or warn on it, which breaks
layout and functionality and undermines the padlock — a trust and (indirectly)
ranking signal.

## High severity

### 1. Active mixed content
- **Definition:** An `https://` page loads a `<script src>`, `<link rel=stylesheet>`,
  `<iframe>`, `<object>`, or `<embed>` over `http://`.
- **Why it matters:** Browsers **block** insecure active content outright. The
  script doesn't run, the stylesheet doesn't apply, the iframe doesn't load — the
  page is visibly broken, and the connection is no longer trustworthy.
- **Fix:** Load the resource over `https://` (most hosts support it — just change
  the scheme), self-host it, or remove it.

### 2. Insecure form action
- **Definition:** A `<form>` on an `https://` page submits to an `http://` action
  URL.
- **Why it matters:** Form data (including credentials) is sent in cleartext;
  browsers show a prominent "Not secure" warning on submit.
- **Fix:** Change the form `action` to `https://`.

## Medium severity

### 3. Passive mixed content
- **Definition:** An `https://` page loads an `<img>`, `<audio>`, `<video>`,
  `<source>`, or `<track>` over `http://`.
- **Why it matters:** Browsers may load it but downgrade the security indicator
  (no padlock) and can block it under stricter settings. It still signals an
  incomplete HTTPS migration.
- **Fix:** Serve the media over `https://`.

## Low severity

### 4. Protocol-relative resource
- **Definition:** A resource URL beginning with `//` (inheriting the page's
  scheme), e.g. `//cdn.example.com/app.js`.
- **Why it matters:** Harmless on an HTTPS page today, but a legacy pattern that
  breaks if the page is ever viewed over HTTP and obscures intent.
- **Fix:** Use explicit `https://` URLs.

## Informational (note, not counted as a mixed-content issue)

- **Insecure page** — the page itself was served over `http://` (or didn't
  redirect to HTTPS). This isn't "mixed" content (there's nothing secure to mix),
  but it's the bigger problem: the whole page is insecure. Reported so the HTTPS
  migration / redirect can be fixed at the source. Cross-check with the
  `redirect-audit` and `site-architecture-audit` skills.
