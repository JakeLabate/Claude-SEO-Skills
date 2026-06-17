# Core Web Vitals Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Core Web Vitals Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages analyzed:** {n} | **Field data (PSI):** {yes/no, strategy} | **Median page weight:** {MB}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview: which vital is the biggest problem and the highest-leverage fixes.}

## Field vitals (PSI / CrUX)

*Only include this section when collected with --psi.*

| Page | LCP | CLS | INP | Lab score |
|---|---|---|---|---|
| / | 3.8s (SLOW) | 0.04 (GOOD) | 240ms (AVERAGE) | 62 |
| ... | ... | ... | ... | ... |

## Issues by vital

### LCP (Largest Contentful Paint)

| Page | Finding | Measurement | Fix |
|---|---|---|---|
| / | LCP image lazy-loaded | loading="lazy" on /hero.jpg | Remove lazy; add fetchpriority="high" + preload |
| / | No text compression | HTML 41KB uncompressed | Enable Brotli/gzip |
| / | Render-blocking JS | 2 scripts in head | Add defer |

### CLS (Cumulative Layout Shift)

| Page | Finding | Measurement | Fix |
|---|---|---|---|
| / | Images missing dimensions | 9 of 24 images | Add width/height or aspect-ratio |

### INP (Interaction to Next Paint)

| Page | Finding | Measurement | Fix |
|---|---|---|---|
| / | Large JS payload | 1.4 MB JS | Code-split, defer, drop unused third parties |
| / | Excessive DOM | 2,310 nodes | Simplify markup, virtualize lists |

### Other page-experience issues

{Missing viewport, missing preconnect, too many requests, page weight, etc.}

## Prioritized action list

1. {Highest-impact fix, naming the page, the measurement, and the expected vital improvement}
2. ...
```

## Guidance

- Map every finding to the vital it affects (LCP / CLS / INP) so the user can prioritize by what is actually failing in the field.
- When PSI field data exists, lead with it (the verdict) and use lab proxies to explain the cause. When it does not exist for a URL, say so and rely on lab proxies.
- Cite the concrete measurement in every row (the file, the byte count, the node count, the attribute) — never generic advice like "optimize images".
- The single highest-leverage LCP fixes are usually: stop lazy-loading the LCP image, enable text compression, and remove render-blocking resources. Call these out first when present.
- Note that measured TTFB reflects the audit machine's network; corroborate with PSI field TTFB before making server-side recommendations.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Order the action list by severity first, then by which Core Web Vital is failing in the field.
