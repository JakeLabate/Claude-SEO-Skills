# Redirect Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Redirect Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**URLs checked:** {n} | **Redirecting:** {n} | **Chain tolerance:** {max-chain} hop(s)

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's redirect health and the biggest wins.}

## Hop distribution

| Hops | URLs |
|---|---|
| 0 (direct 200) | {n} |
| 1 | {n} |
| 2 | {n} |
| 3+ | {n} |

## High-severity issues

### Redirect loops ({n})

| Start URL | Chain | Fix |
|---|---|---|
| ... | A → B → A | ... |

### Redirects ending in errors ({n})

| Start URL | Final URL | Final status | Suggested target |
|---|---|---|---|
| ... | ... | 404 | ... |

### Redirect chains > {max-chain} hop(s) ({n})

| Start URL | Chain (codes) | Final URL | Collapsed redirect |
|---|---|---|---|
| ... | 301 → 301 → 200 | ... | A → C (single 301) |

### HTTPS → HTTP downgrades ({n})

| Start URL | Offending hop |
|---|---|
| ... | https://… → http://… |

## Medium-severity issues

{One subsection per failing check: temporary redirects, meta/JS redirects, mixed codes, canonical-to-redirect. Same table style: source URL, observed chain, fix.}

## Low-severity issues

{Brief list or table: dropped query strings, canonical mismatches.}

## Prioritized action list

1. {Highest-impact fix, with exact rules to change and before/after chains}
2. ...
```

## Guidance

- Every issue row must show the exact hop-by-hop chain (URL and status code per hop), not just "redirects".
- For chains, always state the collapsed single-hop replacement (`A → C`) so the fix is copy-pasteable into the redirect map.
- Base every suggested redirect target on the destination the chain already reaches or the user's migration map; never invent URLs.
- Group templated redirects (e.g., an entire `/old-blog/*` path redirecting through two hops) into one rule-level fix with a few example URLs.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Order the action list by severity first, then by traffic impact (redirects on high-traffic legacy URLs and on canonical/sitemap URLs first).
