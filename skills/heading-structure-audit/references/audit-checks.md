# Heading Structure Audit Checks

Full definitions, thresholds, and rationale for each audit check.

## High severity

### 1. Missing H1

- **Definition:** A page with no `<h1>` element.
- **Why it matters:** The H1 is the strongest on-page structural signal of what the page is about — a headline for both users and search engines. Its absence leaves the page's primary topic ambiguous.
- **Fix:** Add a single H1 stating the page's primary topic, ideally aligned with the title tag and target query.

### 2. No headings at all

- **Definition:** A page with zero heading elements (H1–H6).
- **Why it matters:** A page with no headings has no machine-readable outline; it is hard for screen-reader users to navigate and gives search engines no structural cues. It often indicates content rendered as undifferentiated `<div>`/`<p>` soup.
- **Fix:** Introduce a proper heading outline — one H1 plus H2/H3 section headings reflecting the content's structure.

## Medium severity

### 3. Multiple H1s

- **Definition:** More than one `<h1>` on a page.
- **Why it matters:** While HTML5 technically allows multiple H1s, a single H1 remains the clearest signal of the page's main topic. Multiple H1s usually come from templates (e.g., logo + page title both marked H1) and dilute the signal and the accessibility outline.
- **Fix:** Keep one H1 for the page's primary topic; demote the others to H2 or to non-heading elements.

### 4. Skipped heading level

- **Definition:** The outline descends by more than one level between consecutive headings (e.g., an H2 followed directly by an H4).
- **Why it matters:** Skipped levels break the logical document outline that assistive technology relies on and obscure the content hierarchy.
- **Fix:** Use the next sequential level when nesting (H2 → H3 → H4). Never choose a heading level for its default font size — style with CSS instead.

### 5. Empty heading

- **Definition:** A heading element whose text content is empty after trimming whitespace.
- **Why it matters:** Empty headings create confusing "blank" entries in the accessibility outline and waste a structural slot. They usually result from headings used purely for icons/spacing.
- **Fix:** Remove the empty heading or give it meaningful text. If it exists only for styling, use a non-heading element.

## Low severity

### 6. First heading is not H1

- **Definition:** The first heading encountered on the page is something other than H1 (and an H1 may appear later or not at all).
- **Why it matters:** A well-formed outline opens with the H1. Starting at H2+ suggests the H1 is missing, misplaced, or that section headings were mislabeled.
- **Fix:** Ensure the page's H1 precedes its subordinate headings in source order.

### 7. Heading too long

- **Definition:** Heading text longer than the threshold (default 70 characters).
- **Why it matters:** Very long headings usually mean a sentence or paragraph was marked as a heading. Headings should be concise labels for the section that follows.
- **Fix:** Shorten to a scannable label; move the explanatory detail into body copy beneath the heading.

### 8. Duplicate heading text on one page

- **Definition:** The same heading text appears two or more times on a single page.
- **Why it matters:** Repeated identical headings make the outline ambiguous ("which 'Overview' did you mean?") and often signal templated sections that need differentiation.
- **Fix:** Make each heading specific to its section, or restructure so repeated labels become subheads under a distinguishing parent.

## Informational (note, do not count as issues)

- **Title / H1 mismatch** — the H1 and the `<title>` share no significant words. Sometimes intentional (title optimized for the SERP, H1 for the page), but a large divergence is worth confirming.
- **Very deep outlines** — frequent use of H5/H6 can indicate over-nesting; review whether the content is genuinely that deep.
- **CSS-styled fake headings** — visually bold text that is not marked up as a heading is invisible to this audit and to assistive tech; if the page "looks" structured but reports no headings, suspect this and recommend real heading markup.
