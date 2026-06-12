#!/usr/bin/env python3
"""Check external link targets and run audit checks on an inventory from extract_external_links.py.

Usage:
    python3 check_external_links.py external_links.json [--output audit_report.json]
        [--sponsored-domains amzn.to,partner.example] [--skip-status-checks]

Checks implemented (see references/audit-checks.md):
- broken_links: external links to 4xx/5xx or unresolvable targets (high)
- unflagged_sponsored: links to known affiliate/paid domains missing rel sponsored/nofollow (high)
- insecure_links: http:// external links (medium)
- redirected_links: external links to 3xx targets (medium)
- unsafe_blank: target="_blank" without rel noopener/noreferrer (medium)
- generic_anchors: weak anchor text (low)
- excessive_external: pages with > 100 external links (low)
- sitewide_links: same nav/footer external link on 5+ pages (low)

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict

USER_AGENT = "ExternalLinkAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

GENERIC_ANCHORS = {
    "click here", "here", "read more", "learn more", "more",
    "this page", "link", "this", "source", "website", "see more", "",
}
MAX_EXTERNAL_LINKS = 100
SITEWIDE_MIN_PAGES = 5
AFFILIATE_PARAMS = ("tag=", "ref=", "aff_id=", "affid=", "affiliate=", "utm_medium=affiliate")


def check_status(url):
    """Return final HTTP status without following redirects (HEAD, GET fallback)."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method,
                                     headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            if e.code in (405, 501) and method == "HEAD":
                continue  # retry with GET
            return e.code
        except Exception:
            return 0  # 0 = DNS/network/connection error
    return 0


def main():
    ap = argparse.ArgumentParser(description="Run external link audit checks.")
    ap.add_argument("inventory", help="external_links.json from extract_external_links.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--sponsored-domains", default="",
                    help="comma-separated affiliate/paid domains requiring rel=sponsored")
    ap.add_argument("--skip-status-checks", action="store_true",
                    help="skip network requests; run only static checks")
    args = ap.parse_args()

    with open(args.inventory) as f:
        data = json.load(f)
    links = data["links"]
    sponsored_domains = {d.strip().lower() for d in args.sponsored_domains.split(",") if d.strip()}

    statuses = {}
    if not args.skip_status_checks:
        for target in sorted({l["target"] for l in links}):
            statuses[target] = check_status(target)
            print(f"[{statuses[target]}] {target}", file=sys.stderr)

    findings = {
        "broken_links": [], "unflagged_sponsored": [], "insecure_links": [],
        "redirected_links": [], "unsafe_blank": [], "generic_anchors": [],
        "excessive_external": [], "sitewide_links": [],
    }

    per_page = Counter()
    sitewide = defaultdict(set)  # nav/footer target -> source pages
    domains = Counter()
    domain_followed = Counter()

    for link in links:
        src, target, anchor = link["source"], link["target"], link["anchor"]
        rel = (link.get("rel") or "").lower()
        entry = {"source": src, "target": target, "anchor": anchor}

        per_page[src] += 1
        domains[link["domain"]] += 1
        qualified = any(r in rel for r in ("nofollow", "sponsored", "ugc"))
        if not qualified:
            domain_followed[link["domain"]] += 1
        if link["location"] in ("nav", "footer"):
            sitewide[target].add(src)

        status = statuses.get(target)
        if status is not None:
            if status >= 400 or status == 0:
                findings["broken_links"].append({**entry, "status": status})
            elif 300 <= status < 400:
                findings["redirected_links"].append({**entry, "status": status})

        if target.startswith("http://"):
            findings["insecure_links"].append(entry)

        is_affiliate = (link["domain"] in sponsored_domains
                        or any(p in target for p in AFFILIATE_PARAMS))
        if is_affiliate and "sponsored" not in rel and "nofollow" not in rel:
            findings["unflagged_sponsored"].append({**entry, "rel": link.get("rel")})

        if (link.get("target_attr") == "_blank"
                and "noopener" not in rel and "noreferrer" not in rel):
            findings["unsafe_blank"].append({**entry, "rel": link.get("rel")})

        if anchor.lower().strip() in GENERIC_ANCHORS:
            findings["generic_anchors"].append(entry)

    for page, count in per_page.items():
        if count > MAX_EXTERNAL_LINKS:
            findings["excessive_external"].append({"page": page, "external_links": count})

    for target, sources in sitewide.items():
        if len(sources) >= SITEWIDE_MIN_PAGES:
            findings["sitewide_links"].append({"target": target, "pages": len(sources)})

    severity = {
        "broken_links": "high", "unflagged_sponsored": "high",
        "insecure_links": "medium", "redirected_links": "medium",
        "unsafe_blank": "medium",
        "generic_anchors": "low", "excessive_external": "low", "sitewide_links": "low",
    }
    summary = {
        "pages_crawled": data.get("pages_crawled"),
        "external_links": len(links),
        "unique_domains": len(domains),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low")
        },
    }
    domain_overview = [
        {"domain": d, "links": n, "followed": domain_followed[d],
         "qualified": n - domain_followed[d]}
        for d, n in domains.most_common()
    ]
    report = {"summary": summary, "severity": severity, "findings": findings,
              "domain_overview": domain_overview, "statuses": statuses}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
