#!/usr/bin/env python3
"""Audit a target inventory (from extract_targets.py) for keyword cannibalization.

Usage:
    python3 audit_cannibalization.py target_inventory.json [--output audit_report.json]
        [--brand-suffix "| Acme Co"] [--overlap 0.6]

Checks (see references/audit-checks.md):
- duplicate_title_target (high): 2+ indexable pages with the same normalized title
  core — they target the same query head-on
- overlapping_targets (medium): clusters of pages whose title+H1 keyword sets
  overlap above the threshold (Jaccard) — competing for the same topic
- shared_primary_keyword (low): pages sharing the same significant title bigram

Clustering uses union-find over pairwise Jaccard of each page's keyword signature
(title + H1 + top body keywords). Dependency-free.

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "the", "to", "with", "your", "you", "our", "how",
    "what", "best", "guide", "top",
}


def words(text):
    if not text:
        return []
    return [w for w in re.findall(r"[a-z0-9']+", text.lower())
            if w not in STOPWORDS and len(w) > 2]


def strip_brand(text, brand):
    if not text:
        return ""
    t = text.strip()
    if brand and t.lower().endswith(brand.lower()):
        t = t[: len(t) - len(brand)].rstrip(" |-–:·")
    return t


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def main():
    ap = argparse.ArgumentParser(description="Run keyword-cannibalization audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--brand-suffix", default="")
    ap.add_argument("--overlap", type=float, default=0.6,
                    help="Jaccard overlap of keyword signatures to flag as competing")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {k: [] for k in (
        "duplicate_title_target", "overlapping_targets", "shared_primary_keyword")}

    indexable = {u: p for u, p in pages.items()
                 if p.get("status", 0) == 200 and not p.get("noindex")}

    # 1. Exact duplicate title core.
    title_groups = defaultdict(list)
    for url, p in indexable.items():
        core = strip_brand(p.get("title"), args.brand_suffix)
        key = " ".join(words(core))
        if key:
            title_groups[key].append(url)
    for key, urls in title_groups.items():
        if len(urls) > 1:
            findings["duplicate_title_target"].append(
                {"target": key, "pages": sorted(urls)})

    # 2. Overlapping keyword signatures -> clusters.
    sigs = {}
    for url, p in indexable.items():
        sig = set(words(strip_brand(p.get("title"), args.brand_suffix)))
        sig |= set(words(p.get("h1")))
        sig |= set(p.get("top_keywords", [])[:10])
        if sig:
            sigs[url] = sig

    uf = UnionFind()
    urls = list(sigs)
    edges = []
    for i in range(len(urls)):
        for j in range(i + 1, len(urls)):
            sim = jaccard(sigs[urls[i]], sigs[urls[j]])
            if sim >= args.overlap:
                uf.union(urls[i], urls[j])
                edges.append((urls[i], urls[j], round(sim, 2)))

    clusters = defaultdict(list)
    for url in urls:
        if any(url in (e[0], e[1]) for e in edges):
            clusters[uf.find(url)].append(url)
    for members in clusters.values():
        if len(members) > 1:
            shared = set.intersection(*(sigs[m] for m in members))
            findings["overlapping_targets"].append(
                {"pages": sorted(members),
                 "shared_keywords": sorted(shared)[:10],
                 "size": len(members)})

    # 3. Shared significant title bigram.
    bigram_groups = defaultdict(list)
    for url, p in indexable.items():
        tw = words(strip_brand(p.get("title"), args.brand_suffix))
        for i in range(len(tw) - 1):
            bigram_groups[(tw[i], tw[i + 1])].append(url)
    for bigram, urls_b in bigram_groups.items():
        uniq = sorted(set(urls_b))
        if len(uniq) > 1:
            findings["shared_primary_keyword"].append(
                {"keyword": " ".join(bigram), "pages": uniq})

    severity = {
        "duplicate_title_target": "high",
        "overlapping_targets": "medium",
        "shared_primary_keyword": "low",
    }
    summary = {
        "pages_analyzed": len(indexable),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low", "info")},
    }
    report = {"summary": summary, "severity": severity, "findings": findings}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
