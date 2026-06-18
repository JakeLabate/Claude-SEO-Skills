# Core Web Vitals Audit Checks

Full definitions, thresholds, vital mapping, and rationale for each audit check.

## Background: the three Core Web Vitals

| Vital | Measures | "Good" (field, 75th percentile) |
|---|---|---|
| **LCP** — Largest Contentful Paint | Loading: time until the largest element renders | ≤ 2.5 s |
| **CLS** — Cumulative Layout Shift | Visual stability: unexpected layout movement | ≤ 0.1 |
| **INP** — Interaction to Next Paint | Responsiveness: latency of user interactions | ≤ 200 ms |

LCP/CLS/INP are **field** metrics (real users, reported in CrUX). PSI checks below read the field data directly; the lab-proxy checks diagnose the likely causes without a browser.

## PSI field checks (only when collected with `--psi`)

PageSpeed Insights returns a category per metric: `FAST`, `AVERAGE`, or `SLOW`. These checks are the authoritative pass/fail.

### 1. PSI field LCP poor

- **Definition:** CrUX LCP category is `SLOW` (high) or `AVERAGE` (medium).
- **Fix:** See the LCP fixes below; start with the LCP image and render-blocking resources.

### 2. PSI field CLS poor

- **Definition:** CrUX CLS category is `SLOW` (high) or `AVERAGE` (medium).
- **Fix:** See the CLS fixes below; start with image/embed dimensions and fonts.

### 3. PSI field INP poor

- **Definition:** CrUX INP category is `SLOW` (high) or `AVERAGE` (medium).
- **Fix:** See the INP fixes below; start with JavaScript execution and DOM size.

### 4. PSI Lighthouse score low

- **Definition:** Lab performance score < 50 (high) or < 90 (medium).
- **Why it matters:** A controlled lab snapshot of the page's performance; useful when field data is sparse.
- **Fix:** Address the highest-severity lab-proxy checks below.

## Lab-proxy checks (always)

### 5. No text compression — *affects LCP, TTFB* (high)

- **Definition:** The HTML response is served without gzip/br/deflate and is larger than 5KB.
- **Why it matters:** Uncompressed HTML (and CSS/JS) inflates transfer size and delays first paint and LCP. This is one of the cheapest wins available.
- **Fix:** Enable gzip or Brotli at the server/CDN for all text assets (HTML, CSS, JS, SVG, JSON).

### 6. LCP image is lazy-loaded — *affects LCP* (high)

- **Definition:** The first content image on the page has `loading="lazy"`.
- **Why it matters:** Lazy-loading the above-the-fold/hero image (a common LCP element) delays its request until layout, directly worsening LCP. A frequent and high-impact mistake from blanket lazy-loading.
- **Fix:** Remove `loading="lazy"` from the LCP image; add `fetchpriority="high"` and consider preloading it. Keep lazy-loading for below-the-fold images only.

### 7. Slow TTFB — *affects LCP, INP* (high > 1.8s, medium > budget)

- **Definition:** Measured time to first byte exceeds the budget (default 800 ms). Escalate to high above ~1.8 s.
- **Why it matters:** TTFB is the server-response floor under every other metric; a slow TTFB makes good LCP/INP nearly impossible.
- **Fix:** Add/​tune caching and a CDN, reduce server work, use HTTP/2+; investigate origin latency and database/render time. Note: measured TTFB here includes network conditions from the audit machine; corroborate with PSI field TTFB.

### 8. Excessive DOM size — *affects INP, CLS* (high > 3000, medium > budget)

- **Definition:** Approximate DOM node count exceeds the soft limit (default 1500); escalate above ~3000.
- **Why it matters:** A large DOM increases style/layout cost and slows interaction handling (INP) and rendering.
- **Fix:** Simplify markup, virtualize long lists, remove wrapper-div bloat, and avoid rendering off-screen content.

### 9. Page weight over budget — *affects LCP* (medium)

- **Definition:** Total transfer (HTML + CSS + JS + images) exceeds the budget (default 2.5MB).
- **Why it matters:** Heavy pages load slowly, especially on mobile networks, hurting LCP.
- **Fix:** Compress images and serve modern formats, remove unused CSS/JS, split bundles, and lazy-load below-the-fold media.

### 10. Render-blocking JavaScript — *affects LCP, INP* (medium)

- **Definition:** One or more `<script src>` in `<head>` without `async`, `defer`, or `type="module"`.
- **Why it matters:** Parser-blocking scripts delay rendering and first paint.
- **Fix:** Add `defer` (or `async` for independent scripts), move non-critical JS to the end of `<body>`, and remove unused scripts.

### 11. Render-blocking CSS — *affects LCP* (medium when > 2 files)

- **Definition:** More than two render-blocking stylesheets in `<head>`.
- **Why it matters:** CSS blocks rendering until downloaded and parsed; many separate stylesheets serialize that cost.
- **Fix:** Inline critical CSS, combine stylesheets, and load non-critical CSS asynchronously (e.g., `media` swap or `preload`).

### 12. Images missing width/height — *affects CLS* (medium)

- **Definition:** One or more `<img>` without both `width` and `height` attributes.
- **Why it matters:** Without intrinsic dimensions the browser cannot reserve space, causing layout shift as images load — a leading CLS cause.
- **Fix:** Add `width` and `height` (or CSS `aspect-ratio`) to every image so space is reserved before load.

### 13. Too many requests — *affects LCP* (medium > 80)

- **Definition:** More than 80 subresource requests on the page.
- **Why it matters:** Each request adds connection/scheduling overhead and contends for bandwidth.
- **Fix:** Bundle assets, use sprites/icon fonts/SVG, lazy-load below-the-fold media, and remove unused third parties.

### 14. Large JavaScript payload — *affects INP* (medium > budget)

- **Definition:** Total JS transfer exceeds the budget (default 1MB).
- **Why it matters:** Large JS means long parse/compile/execute time, the primary driver of poor INP and TBT.
- **Fix:** Code-split, tree-shake, defer non-critical JS, and audit heavy third-party scripts.

### 15. Missing viewport meta (medium)

- **Definition:** No `<meta name="viewport">`.
- **Why it matters:** Without it, mobile browsers render at desktop width and zoom out, harming mobile usability and the page-experience signal.
- **Fix:** Add `<meta name="viewport" content="width=device-width, initial-scale=1">`.

### 16. Missing preconnect for third-party origins — *affects LCP* (low)

- **Definition:** The page loads from third-party origins but declares no `preconnect` hints.
- **Why it matters:** Early connection setup (DNS/TCP/TLS) to critical third parties (fonts, CDNs) shaves time off resource loads.
- **Fix:** Add `<link rel="preconnect">` (with `crossorigin` where needed) for the most important third-party origins.

### 17. Large CSS payload — *affects LCP* (low > budget)

- **Definition:** Total CSS transfer exceeds the budget (default 150KB).
- **Fix:** Remove unused CSS, split by route, and minify.

### 18. No lazy-loading on an image-heavy page — *affects LCP* (low)

- **Definition:** More than five images and none use `loading="lazy"`.
- **Why it matters:** Below-the-fold images compete for bandwidth with critical resources during initial load.
- **Fix:** Add `loading="lazy"` to below-the-fold images — but never to the LCP image (see check 6).

## Notes

- Measured TTFB and fetch times reflect the audit machine's network; PSI field TTFB is more representative of real users. Prefer PSI when both are available.
- Brotli-compressed HTML is only decoded if the `brotli` package is installed; otherwise compression is still detected via the `Content-Encoding` header.
- The lab proxies cannot directly measure CLS or INP — they flag the structural causes (missing dimensions, heavy JS, large DOM). Use `--psi` for the actual field values.
