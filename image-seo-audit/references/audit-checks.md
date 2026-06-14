# Image SEO Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Missing alt attribute

- **Definition:** An `<img>` with no `alt` attribute at all (distinct from `alt=""`).
- **Why it matters:** Alt text is the primary accessibility signal for screen-reader users and the main way search engines understand image content (and rank it in image search). A missing attribute is also an accessibility (WCAG) failure.
- **Fix:** Add concise, descriptive alt text that conveys the image's content and function. If the image is purely decorative, use `alt=""` intentionally so assistive tech skips it.

### 2. Broken image

- **Definition:** An image `src` that returns a non-200 HTTP status (404, 403, 5xx) or fails to connect. Requires the inventory to be built with `--check-files`.
- **Why it matters:** Broken images degrade UX, waste crawl budget, and signal a poorly maintained page.
- **Fix:** Restore the asset, correct the path, or remove the reference.

## Medium severity

### 3. Missing width/height

- **Definition:** An `<img>` lacking a `width` and/or `height` attribute.
- **Why it matters:** Without intrinsic dimensions the browser cannot reserve space before the image loads, causing Cumulative Layout Shift (CLS) — a Core Web Vitals metric and a ranking factor.
- **Fix:** Add `width` and `height` attributes matching the image's intrinsic aspect ratio (CSS can still scale it responsively), or set a CSS `aspect-ratio`.

### 4. Oversized file

- **Definition:** An image whose byte size exceeds the budget (default 200 KB). Requires `--check-files`.
- **Why it matters:** Large images are the most common cause of slow Largest Contentful Paint (LCP) and heavy mobile data use.
- **Fix:** Compress, resize to the largest rendered dimension, and serve a modern format. Use responsive `srcset` so small screens download small images.

## Low severity

### 5. Not lazy-loaded

- **Definition:** An image at or beyond the configured position (default: any image after the first) that lacks `loading="lazy"`.
- **Why it matters:** Eagerly loading off-screen images delays the loading of content the user can actually see.
- **Caveat:** The **first**, above-the-fold / LCP image should **not** be lazy-loaded (it delays LCP). The check skips the first image by default; confirm which images are above the fold before applying fixes.
- **Fix:** Add `loading="lazy"` to below-the-fold images; leave the LCP image eager.

### 6. Legacy format with no modern source

- **Definition:** A JPEG, PNG, or GIF served by a plain `<img>` not wrapped in a `<picture>` that offers a modern source.
- **Why it matters:** WebP and AVIF are typically 25–50% smaller at equivalent quality, improving LCP and bandwidth.
- **Fix:** Serve WebP/AVIF via `<picture>` with a legacy `<img>` fallback, or have the CDN/image pipeline negotiate format by `Accept` header.

### 7. Generic filename

- **Definition:** Uninformative filenames such as `IMG_1234`, `DSC0001`, `screenshot`, `untitled`, `download`, all-digit, or hash-like names.
- **Why it matters:** Filenames are a minor but real relevance signal for image search; descriptive names help.
- **Fix:** Rename to short, hyphenated, descriptive filenames (e.g., `red-running-shoe-side.webp`).

### 8. Alt text too long

- **Definition:** Alt text longer than 125 characters.
- **Why it matters:** Some screen readers truncate around this length, and very long alt usually means description belongs in body copy or a caption.
- **Fix:** Tighten to the essential content; move extended detail to a visible caption or `figcaption`.

### 9. Redundant alt prefix

- **Definition:** Alt text beginning with "image of", "picture of", "photo of", or similar.
- **Why it matters:** Assistive tech already announces the element as an image, so the prefix is redundant noise.
- **Fix:** Remove the prefix and describe the subject directly.

## Informational (note, do not count as issues)

- **Empty alt (`alt=""`)** — valid and correct for decorative images, but listed so the user can confirm each one is genuinely decorative and not an accidental empty value on a meaningful image.
- **Duplicate alt text** — the same non-empty alt reused across three or more distinct images. Sometimes legitimate (repeated logo), but often a templating bug that applies one description to many different images.
- **Background images in CSS** — this audit only sees `<img>` and `<picture>` elements; images set via CSS `background-image` are invisible to crawlers and to image search. Note this limitation if visual images appear missing from the inventory.
