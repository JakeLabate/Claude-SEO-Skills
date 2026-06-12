# Schema Markup Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Schema Markup Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages scanned:** {n} | **Schema blocks found:** {n} | **Types in use:** {Type1, Type2, ...}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's structured data health and the biggest wins.}

## Coverage map

| Page type | Pages | Expected schema | Present | Gap |
|---|---|---|---|---|
| Product pages | {n} | Product, BreadcrumbList | Product only | BreadcrumbList missing |
| ... | ... | ... | ... | ... |

## High-severity issues

### Invalid JSON-LD ({n})

| Page | Error | Location | Suggested fix |
|---|---|---|---|
| ... | Trailing comma | line {n} | ... |

### Missing required properties ({n})

| Page | Schema type | Missing property | Suggested value source |
|---|---|---|---|
| ... | Product | offers.priceCurrency | Displayed price on page |

### Missing schema on key pages ({n})

| Page / template | Expected type | Recommendation |
|---|---|---|
| ... | ... | ... |

## Medium-severity issues

{One subsection per failing check, same table style: affected pages, schema type, property, specific fix.}

## Low-severity issues

{Brief list or table.}

## Opportunities

{Schema types worth adding for rich result eligibility, with the pages/templates to add them to and a ready-to-use JSON-LD snippet per template.}

## Prioritized action list

1. {Highest-impact fix, with exact pages and corrected JSON-LD snippets}
2. ...

## Validation checklist

- [ ] Re-test one URL per fixed template in Google's Rich Results Test
- [ ] Confirm no parse errors at validator.schema.org
- [ ] Monitor Search Console > Enhancements for error/warning trends after deploy
```

Guidelines:

- Include a corrected, copy-pasteable JSON-LD snippet for every template-level fix, populated with real values from the page.
- Group issues by template when many pages share the same problem; list a few example URLs rather than hundreds of rows.
- Only include sections that have findings.
