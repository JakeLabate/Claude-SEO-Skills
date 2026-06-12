#!/usr/bin/env python3
"""Validate a schema inventory JSON file and produce an audit report JSON.

Usage:
    python3 validate_schema.py schema_inventory.json [--output audit_report.json]

Runs the checks defined in references/audit-checks.md against the inventory
produced by extract_schema.py. Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
from collections import Counter

# Required / recommended properties per type for Google rich result eligibility.
# Required-property entries support dotted paths (e.g., "offers.price").
TYPE_RULES = {
    "Product": {
        "required": ["name", "image", "offers", "offers.price", "offers.priceCurrency"],
        "recommended": ["offers.availability", "aggregateRating", "review", "sku", "brand", "description"],
    },
    "Article": {
        "required": ["headline", "image"],
        "recommended": ["author", "datePublished", "dateModified", "publisher", "mainEntityOfPage"],
    },
    "BlogPosting": {
        "required": ["headline", "image"],
        "recommended": ["author", "datePublished", "dateModified", "publisher", "mainEntityOfPage"],
    },
    "NewsArticle": {
        "required": ["headline", "image"],
        "recommended": ["author", "datePublished", "dateModified", "publisher", "mainEntityOfPage"],
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "openingHoursSpecification", "geo", "url", "image", "priceRange"],
    },
    "Organization": {
        "required": ["name"],
        "recommended": ["url", "logo", "sameAs", "contactPoint"],
    },
    "WebSite": {
        "required": ["name", "url"],
        "recommended": [],
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "recommended": [],
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "recommended": [],
    },
    "Event": {
        "required": ["name", "startDate", "location"],
        "recommended": ["endDate", "eventStatus", "eventAttendanceMode", "offers", "performer", "image", "organizer"],
    },
    "JobPosting": {
        "required": ["title", "description", "datePosted", "hiringOrganization", "jobLocation"],
        "recommended": ["baseSalary", "employmentType", "validThrough", "identifier"],
    },
    "Recipe": {
        "required": ["name", "image"],
        "recommended": ["author", "description", "prepTime", "cookTime", "recipeIngredient", "recipeInstructions", "aggregateRating"],
    },
    "VideoObject": {
        "required": ["name", "thumbnailUrl", "uploadDate"],
        "recommended": ["description", "duration", "contentUrl", "embedUrl"],
    },
    "Review": {
        "required": ["reviewRating", "author"],
        "recommended": ["itemReviewed", "datePublished"],
    },
    "AggregateRating": {
        "required": ["ratingValue"],
        "recommended": ["ratingCount", "reviewCount", "bestRating"],
    },
}

# Types whose Google rich results are retired or heavily restricted.
DEPRECATED_TYPES = {
    "HowTo": "Google retired HowTo rich results (Sept 2023); markup yields no rich result benefit.",
    "FAQPage": "FAQ rich results are limited to well-known, authoritative government and health websites.",
    "SpeakableSpecification": "Speakable remains in limited beta with negligible adoption.",
}

ISO8601_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:?\d{2}|Z)?)?$")
PRICE_RE = re.compile(r"^\d+(\.\d+)?$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def has_prop(data, path):
    """Check a (possibly dotted) property path on a JSON-LD-ish dict."""
    node = data
    for part in path.split("."):
        if isinstance(node, list):
            node = node[0] if node else None
        if not isinstance(node, dict):
            return False
        if part not in node or node[part] in (None, "", []):
            return False
        node = node[part]
    return True


def get_prop(data, path):
    node = data
    for part in path.split("."):
        if isinstance(node, list):
            node = node[0] if node else None
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def check_value_formats(url, block, issues):
    data = block["data"]
    fmt_checks = [
        ("offers.price", PRICE_RE, "price should be a plain number string, e.g. \"10.00\" (no currency symbols)"),
        ("offers.priceCurrency", CURRENCY_RE, "priceCurrency should be an ISO 4217 code, e.g. \"USD\""),
        ("datePublished", ISO8601_DATE, "datePublished should be an ISO 8601 date"),
        ("dateModified", ISO8601_DATE, "dateModified should be an ISO 8601 date"),
        ("startDate", ISO8601_DATE, "startDate should be an ISO 8601 date"),
        ("datePosted", ISO8601_DATE, "datePosted should be an ISO 8601 date"),
        ("uploadDate", ISO8601_DATE, "uploadDate should be an ISO 8601 date"),
    ]
    for path, regex, message in fmt_checks:
        value = get_prop(data, path)
        if isinstance(value, (int, float)):
            continue
        if isinstance(value, str) and value and not regex.match(value.strip()):
            issues.append({
                "check": "invalid_property_value", "severity": "medium", "page": url,
                "type": "/".join(block["types"][:1]) or "(unknown)",
                "detail": f"{path} = {value!r}: {message}",
            })
    avail = get_prop(data, "offers.availability")
    if isinstance(avail, str) and avail and "schema.org" not in avail:
        issues.append({
            "check": "invalid_property_value", "severity": "medium", "page": url,
            "type": block["types"][0] if block["types"] else "(unknown)",
            "detail": f"offers.availability = {avail!r}: should be a schema.org URL, e.g. \"https://schema.org/InStock\"",
        })
    image = get_prop(data, "image")
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url")
    if isinstance(image, str) and image and not image.startswith(("http://", "https://")):
        issues.append({
            "check": "invalid_property_value", "severity": "medium", "page": url,
            "type": block["types"][0] if block["types"] else "(unknown)",
            "detail": f"image = {image!r}: should be an absolute HTTPS URL",
        })


def audit(inventory):
    issues = []
    pages = inventory.get("pages", {})
    type_counts = Counter()

    homepage_types = set()
    homepage_url = None
    for url in pages:
        path = re.sub(r"^https?://[^/]+", "", url) or "/"
        if path in ("/", "/index.html", "index.html"):
            homepage_url = url

    for url, page in pages.items():
        blocks = page.get("schema_blocks", [])

        # 1. Invalid JSON-LD
        for err in page.get("jsonld_errors", []):
            issues.append({
                "check": "invalid_jsonld", "severity": "high", "page": url,
                "type": "(unparseable)",
                "detail": f"JSON-LD block {err['block_index']}: {err['error']}",
            })

        seen_types_on_page = Counter()
        formats_per_type = {}
        for block in blocks:
            primary = block["types"][0] if block["types"] else None
            if not primary:
                issues.append({
                    "check": "missing_type", "severity": "high", "page": url,
                    "type": "(none)", "detail": "Schema block has no @type",
                })
                continue
            type_counts[primary] += 1
            seen_types_on_page[primary] += 1
            formats_per_type.setdefault(primary, set()).add(block["format"])
            if url == homepage_url:
                homepage_types.update(block["types"])

            rules = TYPE_RULES.get(primary)
            if rules:
                # 2. Missing required properties
                for prop in rules["required"]:
                    if not has_prop(block["data"], prop):
                        issues.append({
                            "check": "missing_required_property", "severity": "high",
                            "page": url, "type": primary,
                            "detail": f"Missing required property: {prop}",
                        })
                # 4. Missing recommended properties
                missing_rec = [p for p in rules["recommended"] if not has_prop(block["data"], p)]
                if missing_rec:
                    issues.append({
                        "check": "missing_recommended_properties", "severity": "medium",
                        "page": url, "type": primary,
                        "detail": "Missing recommended: " + ", ".join(missing_rec),
                    })

            # 7. Deprecated types
            for t in block["types"]:
                if t in DEPRECATED_TYPES:
                    issues.append({
                        "check": "deprecated_type", "severity": "medium", "page": url,
                        "type": t, "detail": DEPRECATED_TYPES[t],
                    })

            # 9. Invalid property values
            check_value_formats(url, block, issues)

        # 6. Duplicate blocks of the same type
        for t, count in seen_types_on_page.items():
            if count > 1 and t in TYPE_RULES and t not in ("Review",):
                issues.append({
                    "check": "duplicate_schema_blocks", "severity": "medium", "page": url,
                    "type": t, "detail": f"{count} blocks of type {t} on one page — verify they are distinct entities or merge them",
                })

        # 11. Mixed formats for the same type
        for t, formats in formats_per_type.items():
            if len(formats) > 1:
                issues.append({
                    "check": "mixed_formats", "severity": "low", "page": url,
                    "type": t, "detail": f"Type {t} marked up in multiple formats ({', '.join(sorted(formats))}); standardize on JSON-LD",
                })

    # 8. Homepage Organization / WebSite
    if homepage_url is not None:
        if not ({"Organization", "LocalBusiness"} & homepage_types):
            issues.append({
                "check": "missing_homepage_schema", "severity": "medium", "page": homepage_url,
                "type": "Organization", "detail": "Homepage has no Organization or LocalBusiness schema",
            })
        if "WebSite" not in homepage_types:
            issues.append({
                "check": "missing_homepage_schema", "severity": "medium", "page": homepage_url,
                "type": "WebSite", "detail": "Homepage has no WebSite schema",
            })

    # 3. Pages with no structured data at all (coverage gap candidates)
    no_schema = [url for url, p in pages.items()
                 if not p.get("schema_blocks") and not p.get("jsonld_errors")
                 and p.get("status", 0) == 200]
    for url in no_schema:
        issues.append({
            "check": "no_structured_data", "severity": "info", "page": url,
            "type": "(none)",
            "detail": "Page has no structured data; check expected schema for its page type (see references/audit-checks.md)",
        })

    severity_counts = Counter(i["severity"] for i in issues)
    return {
        "summary": {
            "pages_scanned": len(pages),
            "schema_blocks": sum(len(p.get("schema_blocks", [])) for p in pages.values()),
            "types_in_use": dict(type_counts),
            "issues_by_severity": dict(severity_counts),
        },
        "issues": issues,
    }


def main():
    ap = argparse.ArgumentParser(description="Validate a schema inventory and produce an audit report")
    ap.add_argument("inventory", help="Path to schema_inventory.json from extract_schema.py")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        inventory = json.load(f)

    report = audit(inventory)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    s = report["summary"]
    print(f"Pages: {s['pages_scanned']} | Blocks: {s['schema_blocks']} | "
          f"Issues: {s['issues_by_severity']}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
