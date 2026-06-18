# Meta Data Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Missing or empty title tag

- **Definition:** A page with no `<title>` element, or one whose text is empty after trimming whitespace.
- **Why it matters:** The title is the strongest on-page relevance signal and the headline of the SERP snippet. Without one, search engines generate their own, usually badly.
- **Fix:** Add a unique, descriptive title near 60 characters that leads with the page's primary topic.

### 2. Missing or empty meta description

- **Definition:** A page with no `<meta name="description">`, or one whose `content` is empty after trimming whitespace.
- **Why it matters:** Without a description, search engines pull arbitrary page text into the snippet, which usually hurts click-through rate.
- **Fix:** Add a description near 155 characters that summarizes the page and gives searchers a reason to click.

### 3. Duplicate titles across pages

- **Definition:** Two or more indexable pages sharing an identical title (compared after stripping a known brand suffix and normalizing whitespace).
- **Why it matters:** Duplicate titles make pages compete with each other, hide what differentiates each page, and often indicate templated metadata that was never filled in.
- **Fix:** Give each page a unique title reflecting its specific topic. For templated pages, interpolate the differentiating value (product name, location, category).

### 4. Duplicate meta descriptions across pages

- **Definition:** Two or more indexable pages sharing an identical meta description.
- **Why it matters:** Same problem as duplicate titles: snippets stop differentiating pages, and search engines are more likely to ignore the description entirely.
- **Fix:** Write page-specific descriptions, or template them with page-specific values.

## Medium severity

### 5. Multiple title tags or meta descriptions on one page

- **Definition:** More than one `<title>` element, or more than one `<meta name="description">`, in a single document.
- **Why it matters:** Search engines pick one unpredictably; the duplicates usually come from a CMS theme plus an SEO plugin both injecting metadata.
- **Fix:** Remove all but one authoritative tag; fix the template or plugin conflict that produced the duplicates.

### 6. Title too long

- **Definition:** Title text over 60 characters.
- **Threshold:** Flag over 60; treat over 70 as certain truncation. Google truncates at roughly 600 pixels, and 60 characters is the practical proxy.
- **Why it matters:** Truncated titles lose their ending (often the call to action or differentiator) behind an ellipsis.
- **Fix:** Rewrite to lead with the primary topic and fit within roughly 60 characters; cut filler words and move the brand to the end or drop it.

### 7. Title too short

- **Definition:** Title text under 30 characters.
- **Why it matters:** Very short titles waste the strongest snippet real estate and are usually generic ("Blog", "About").
- **Fix:** Expand with the page's specific topic and a differentiator; aim for 50–60 characters.

### 8. Description too long

- **Definition:** Meta description over 160 characters.
- **Threshold:** Flag over 160; treat over 200 as certain truncation. Google rewrites or truncates beyond roughly 155–160 characters on desktop, fewer on mobile.
- **Fix:** Front-load the key message in the first 120 characters and trim to roughly 155.

### 9. Description too short

- **Definition:** Meta description under 70 characters.
- **Why it matters:** Wastes snippet space and competes poorly against fuller competitor snippets.
- **Fix:** Expand toward 120–155 characters with specifics: what the page covers, for whom, and why to click.

### 10. Generic or boilerplate titles

- **Definition:** Titles that are non-descriptive on their own.
- **Detection list:** "home", "homepage", "index", "untitled", "new page", "default", "page", "welcome", "blog", "about", "contact", "products", "services" (bare, with no qualifier), and titles that equal the brand suffix alone.
- **Why it matters:** Generic titles carry no relevance signal and no reason to click.
- **Fix:** Replace with a specific topic plus differentiator, keeping the brand at the end.

## Low severity

### 11. Description duplicates the title

- **Definition:** A meta description identical to (or wholly contained in) the page title.
- **Why it matters:** The snippet repeats itself instead of adding a second message; search engines will usually substitute their own text.
- **Fix:** Write a description that complements the title with detail the title could not fit.

### 12. Keyword stuffing in the title

- **Definition:** The same significant word appearing three or more times in one title, or comma-separated keyword lists as a title.
- **Why it matters:** Looks spammy in the SERP, depresses click-through, and invites title rewrites by Google.
- **Fix:** Use the keyword once, naturally, and spend the remaining characters on a differentiator.

## Informational (note, do not count as issues)

- **Title/H1 mismatch** — the title and the first `<h1>` describe different topics. Often deliberate (titles optimized for SERPs, H1s for the page), but large divergence is worth a look.
- **og:title / og:description divergence** — social metadata that differs wildly from the SERP metadata; confirm it is intentional.
- **Noindexed pages with metadata issues** — excluded from duplicate checks by default; list separately if the user wants full coverage.
- **Identical title and description across pagination** — paginated series (`?page=2`) often inherit page 1 metadata; recommend appending page numbers.
