# Schema Markup Audit Checks

Full definitions, severities, and rationale for each audit check, plus required/recommended properties for common schema types.

## High severity

### 1. Invalid JSON-LD

- **Definition:** A `<script type="application/ld+json">` block whose contents fail JSON parsing (trailing commas, unescaped quotes, comments, truncation).
- **Why it matters:** Invalid blocks are ignored entirely by search engines — the page gets no structured data benefit from them.
- **Fix:** Correct the JSON syntax. Validate with a JSON parser before deploying.

### 2. Missing required properties

- **Definition:** A schema block declares a type but omits properties Google requires for that type's rich result (see property tables below).
- **Why it matters:** Missing required properties make the item ineligible for rich results and appear as errors in Search Console.
- **Fix:** Add each required property with a real value taken from the visible page content.

### 3. Missing schema on key page types

- **Definition:** A page whose template clearly maps to a schema type but has no matching markup (e.g., product pages without `Product`, articles without `Article`, location pages without `LocalBusiness`).
- **Why it matters:** The page forfeits rich result eligibility competitors may have.
- **Fix:** Add JSON-LD markup of the appropriate type to the page template.

## Medium severity

### 4. Missing recommended properties

- **Definition:** Required properties are present, but recommended ones (per Google's rich result docs) are missing.
- **Why it matters:** Recommended properties improve rich result quality and appear as warnings in Search Console.
- **Fix:** Add recommended properties where the data exists; do not fabricate values.

### 5. Schema/content mismatch

- **Definition:** Markup describes content not visible on the page (e.g., review stars with no visible reviews, FAQ markup without the Q&A on the page, prices that differ from the displayed price).
- **Why it matters:** Violates Google's structured data guidelines and can trigger manual actions.
- **Fix:** Make markup mirror visible page content exactly; remove markup for content that isn't there.

### 6. Conflicting or duplicate schema blocks

- **Definition:** Multiple blocks on one page declare the same entity with different values (e.g., two `Product` blocks with different prices), or the same block is duplicated.
- **Why it matters:** Search engines may pick the wrong values or ignore both.
- **Fix:** Keep one authoritative block per entity per page; merge or remove the rest.

### 7. Deprecated types or properties

- **Definition:** Markup uses types whose rich results Google has retired or restricted (e.g., `HowTo` retired, `FAQPage` limited to well-known authoritative government and health sites), or schema.org-deprecated properties.
- **Why it matters:** Maintenance burden with no rich result benefit; signals stale implementation.
- **Fix:** Remove or deprioritize the markup; redirect effort to types that still produce rich results.

### 8. Missing Organization / WebSite schema on the homepage

- **Definition:** The homepage lacks `Organization` (or `LocalBusiness`) and `WebSite` markup.
- **Why it matters:** These feed Google's knowledge panel, sitelinks, and brand entity understanding.
- **Fix:** Add `Organization` with `name`, `url`, `logo`, and `sameAs` (social profiles), plus `WebSite` with `name` and `url`.

### 9. Broken or invalid property values

- **Definition:** Properties with malformed values: relative or 404 image URLs, invalid ISO 8601 dates, invalid currency codes, prices as `"$10"` instead of `"10.00"`, wrong enumeration values (e.g., `availability` not a `schema.org/ItemAvailability` URL).
- **Why it matters:** Invalid values are treated as missing.
- **Fix:** Use absolute HTTPS URLs, ISO 8601 dates, ISO 4217 currency codes, and schema.org enumeration URLs.

### 10. Missing or mismatched entity linking (`@id` / `url`)

- **Definition:** Entities that should reference each other (e.g., `Article.publisher` → `Organization`) are disconnected, or `url` values don't match the canonical URL.
- **Why it matters:** Weakens entity graph consistency across the site.
- **Fix:** Use stable `@id` values (e.g., `https://example.com/#organization`) and reference them across pages; align `url` with canonicals.

## Low severity

### 11. Mixed formats for the same entity

- **Definition:** The same entity is marked up in both JSON-LD and Microdata/RDFa on the same page (often a CMS theme plus a plugin).
- **Why it matters:** Risk of conflicting values; harder to maintain.
- **Fix:** Standardize on JSON-LD and remove the duplicate Microdata/RDFa.

### 12. Missing optional enhancements

- **Definition:** Easy wins not implemented: `BreadcrumbList` on inner pages, `sameAs` social links, `ImageObject` for logos, `inLanguage`, `author` with a `Person` profile page.
- **Why it matters:** Incremental gains in rich result quality and entity clarity.
- **Fix:** Add where data is readily available.

## Required and recommended properties by type

Based on Google's rich result documentation. "Required" means required for rich result eligibility.

### Product (with offer)

- **Required:** `name`, `offers` (with `price`, `priceCurrency`), `image`
- **Recommended:** `offers.availability`, `offers.priceValidUntil`, `aggregateRating`, `review`, `sku`, `gtin`/`mpn`, `brand`, `description`

### Article / BlogPosting / NewsArticle

- **Required:** none strictly, but `headline` and `image` are needed for rich display
- **Recommended:** `author` (with `name` and `url`), `datePublished`, `dateModified`, `publisher`, `mainEntityOfPage`

### LocalBusiness

- **Required:** `name`, `address`
- **Recommended:** `telephone`, `openingHoursSpecification`, `geo`, `url`, `image`, `priceRange`, `sameAs`

### Organization

- **Recommended:** `name`, `url`, `logo`, `sameAs`, `contactPoint`

### WebSite

- **Recommended:** `name`, `url`; add `potentialAction` (`SearchAction`) only if the site has internal search.

### BreadcrumbList

- **Required:** `itemListElement` with `ListItem`s, each with `position`, `name`, and `item` (URL; omit on the last item)

### FAQPage

- **Required:** `mainEntity` of `Question` items, each with `acceptedAnswer`
- **Note:** Rich results limited to authoritative government/health sites; markup must mirror visible Q&A.

### Review / AggregateRating

- **Required:** `reviewRating`/`ratingValue`, `author` (for `Review`), `itemReviewed` (when standalone)
- **Note:** Self-serving reviews (a business marking up reviews of itself via `Organization`/`LocalBusiness`) are ineligible for review rich results.

### Event

- **Required:** `name`, `startDate`, `location`
- **Recommended:** `endDate`, `eventStatus`, `eventAttendanceMode`, `offers`, `performer`, `image`, `organizer`

### JobPosting

- **Required:** `title`, `description`, `datePosted`, `hiringOrganization`, `jobLocation` (or `applicantLocationRequirements` + `jobLocationType` for remote)
- **Recommended:** `baseSalary`, `employmentType`, `validThrough`, `identifier`

### Recipe

- **Required:** `name`, `image`
- **Recommended:** `author`, `datePublished`, `description`, `prepTime`, `cookTime`, `totalTime`, `recipeIngredient`, `recipeInstructions`, `recipeYield`, `nutrition`, `aggregateRating`, `video`

### VideoObject

- **Required:** `name`, `thumbnailUrl`, `uploadDate`
- **Recommended:** `description`, `duration`, `contentUrl`, `embedUrl`, `interactionStatistic`

## Expected schema by page type

Use this mapping to detect coverage gaps (adjust with the user's business context):

| Page type | Expected schema |
|---|---|
| Homepage | `Organization` (or `LocalBusiness`), `WebSite` |
| Product page | `Product` with `offers`, `BreadcrumbList` |
| Category/listing page | `BreadcrumbList`; optionally `ItemList` |
| Blog post / article | `Article`/`BlogPosting`, `BreadcrumbList` |
| Contact / location page | `LocalBusiness` with address, hours |
| Event page | `Event` |
| Job listing | `JobPosting` |
| Recipe page | `Recipe` |
| Video page | `VideoObject` |
