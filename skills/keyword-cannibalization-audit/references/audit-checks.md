# Keyword Cannibalization Audit Checks

Definitions, thresholds, and rationale. **Cannibalization** is when several pages
on the same site target the same query, so they compete with each other in the
results — splitting links, clicks, and authority, and letting the engine pick the
"wrong" page. This audit finds groups of pages that look like they chase the same
keyword, based on their titles, H1s, and body keywords.

These are *candidates for review*: some overlap is legitimate (a hub page plus its
children). The audit surfaces the clusters; a human decides which to consolidate.

## High severity

### 1. Duplicate title target
- **Definition:** Two or more indexable pages whose title (after removing a known
  brand suffix and stopwords) normalizes to the same phrase.
- **Why it matters:** Identical title targets are the clearest cannibalization
  signal — the pages explicitly chase the same query.
- **Fix:** Decide the one canonical page for that query; differentiate, merge, or
  redirect the others; and 301 or canonicalize as appropriate.

## Medium severity

### 2. Overlapping targets (keyword cluster)
- **Definition:** A cluster of pages whose keyword signatures (title + H1 + top
  body keywords) overlap above the threshold (default Jaccard ≥ 0.6).
- **Why it matters:** Even with different titles, pages that share most of their
  topic vocabulary compete for the same searches and dilute each other.
- **Fix:** Establish a clear hierarchy — one primary page per intent, supporting
  pages that target distinct sub-queries and link up to the primary. Consolidate
  true overlaps; differentiate genuine variants.

## Low severity

### 3. Shared primary keyword (title bigram)
- **Definition:** Multiple pages share the same significant two-word phrase in
  their title.
- **Why it matters:** A weaker hint of overlapping intent; often fine (a product
  line), sometimes the start of cannibalization.
- **Fix:** Review the set; ensure each page targets a distinct angle of the shared
  phrase.

## Reading the results

- **Confirm intent before acting.** A category page and its articles *should*
  share vocabulary. The fix is usually a clearer hierarchy, not deletion.
- **Tune `--overlap`.** Lower it to surface looser themes, raise it for only the
  tightest competitors. Pass `--brand-suffix "| Brand"` so brand words don't
  inflate title similarity.
- **Cross-check Search Console.** True cannibalization shows as multiple URLs
  ranking and swapping for the same query; use this audit to find candidates, then
  confirm with real query data before consolidating.
- Related: `meta-data-audit` (duplicate titles) and `content-quality-audit`
  (duplicate/near-duplicate bodies) overlap with this audit from different angles.
