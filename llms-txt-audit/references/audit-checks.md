# llms.txt Audit Checks

Full definitions, thresholds, and rationale for each audit check.

The guiding principle: **`/llms.txt` should be a valid markdown file, served as plain text/markdown from the site root, that opens with an H1 title and a one-line summary and then offers curated sections of well-described links — each pointing to a final, canonical, reachable `200` page.** It is a human- and LLM-readable map of your best content, so structure and link health are everything. The spec lives at https://llmstxt.org.

## High severity

### 1. /llms.txt missing

- **Definition:** `/llms.txt` returns a non-200 status (404, error, etc.).
- **Why it matters:** Without the file, AI assistants have no curated entry point to the site and fall back to crawling or guessing. For a site that wants strong LLM discoverability, the absence of the file is the headline finding.
- **Fix:** Create `/llms.txt` with an H1 title, a `>` summary, and at least one `## ` section of curated links. (Note: the standard is emerging and optional — if the user does not want one, this is informational rather than a defect.)

### 2. Served as HTML

- **Definition:** The response body is an HTML document rather than markdown/plain text.
- **Why it matters:** A rendered HTML page (or a soft-404) is not a parseable llms.txt; LLM tooling expects raw markdown. It usually means a catch-all route is serving the path.
- **Fix:** Serve the raw markdown file directly; return a genuine `404` if there is no file.

### 3. Missing H1 title

- **Definition:** The file has no single top-level `# Title` heading.
- **Why it matters:** The H1 project/site name is the only required element in the spec. Without it the file is not a valid llms.txt and consumers may reject or misparse it.
- **Fix:** Add one `# Project Name` heading as the first line.

### 4. Referenced link returns an error

- **Definition:** A link listed in llms.txt returns 4xx, 5xx, or a connection error.
- **Why it matters:** The whole point of the file is to send LLMs to useful pages; dead links waste that and signal a stale, untrusted file.
- **Fix:** Replace the link with the correct live URL, or remove it.

## Medium severity

### 5. /llms.txt redirects

- **Definition:** `/llms.txt` returns a 3xx redirect instead of the file directly.
- **Why it matters:** Consumers may not follow redirects for this file. It should live at the canonical root path and return the content directly.
- **Fix:** Serve `/llms.txt` with a `200` at the root, no redirect.

### 6. Referenced link redirects

- **Definition:** A listed link returns a 3xx redirect rather than a final 200.
- **Why it matters:** llms.txt should point straight to destinations. Redirecting entries add a hop and suggest the file was not updated after content moved.
- **Fix:** Replace the link with its final destination URL.

### 7. Missing summary

- **Definition:** There is no `>` blockquote summary immediately after the H1.
- **Why it matters:** The summary is the spec's recommended one-line orientation for an LLM with limited context; without it the file is less useful at a glance.
- **Fix:** Add a single `> One-sentence description of the project.` line under the H1.

### 8. Link missing a description

- **Definition:** A list link has no trailing description (`- [title](url)` with nothing after it).
- **Why it matters:** Descriptions tell an LLM what each link is for and when to use it. Bare links force guessing from the URL alone.
- **Fix:** Append `: one-line description` to each link item.

### 9. Malformed list item

- **Definition:** A list item under a section is not a valid markdown link (`- [name](url)`).
- **Why it matters:** Parsers extract links by this exact shape; a malformed item is dropped or misread, so the content it pointed to is lost.
- **Fix:** Rewrite the item as `- [Descriptive title](https://absolute-url): description.`

### 10. Link on the wrong host

- **Definition:** A listed link is on a different host than the site (different subdomain, `www` mismatch, or external domain).
- **Why it matters:** llms.txt should map *this* site's content. Off-host links may be intentional (e.g., docs on a subdomain) but are often mistakes or non-canonical hosts.
- **Fix:** Point links at the canonical host, or confirm the off-host link is intended.

### 11. Linked page is noindex or robots-blocked

- **Definition:** A referenced page is marked `noindex` (meta robots / X-Robots-Tag) or its path is disallowed in robots.txt.
- **Why it matters:** Featuring a page in llms.txt while telling crawlers to ignore or not index it is a contradictory signal and a sign the curation is stale.
- **Fix:** Either promote the page (remove the block/noindex if it should be surfaced) or drop it from llms.txt.

### 12. Wrong content type

- **Definition:** The file is served with a `Content-Type` other than `text/markdown` or `text/plain`.
- **Why it matters:** Some consumers check the content type; an unexpected type (e.g., `application/octet-stream` or `text/html`) can cause the file to be skipped or downloaded instead of read.
- **Fix:** Serve it as `text/markdown; charset=utf-8` (or `text/plain`).

## Low severity

### 13. Relative URL instead of absolute

- **Definition:** A link uses a relative path (`/docs`) rather than an absolute URL.
- **Why it matters:** llms.txt is frequently fetched and processed out of context, where relative URLs cannot be resolved. The spec recommends absolute URLs.
- **Fix:** Use full `https://` URLs for every link.

### 14. No sections / no links

- **Definition:** The file has no `## ` sections, or sections contain no links.
- **Why it matters:** A title and summary with no curated links provides little value to an LLM.
- **Fix:** Add `## ` sections grouping your most important pages as described links.

### 15. Duplicate link

- **Definition:** The same URL appears in more than one place in the file.
- **Why it matters:** Harmless but noisy; usually a curation slip that inflates the list.
- **Fix:** List each URL once, in its most relevant section.

### 16. /llms-full.txt missing

- **Definition:** No `/llms-full.txt` is present.
- **Why it matters:** Purely informational. `llms-full.txt` (the full expanded content in one file) is optional; some sites offer it for full-content ingestion, but it is not required.
- **Fix:** If full-content ingestion is desired, generate `/llms-full.txt` with the expanded page contents. Otherwise ignore.
