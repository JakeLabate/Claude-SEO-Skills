# Claude-SEO-Skills

A collection of [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) for SEO tasks. Each top-level folder is a self-contained, fully functional Claude skill.

## Skill architecture

Every skill folder follows the standard Claude skill structure:

```
skill-name/
├── SKILL.md          # Required — YAML frontmatter (name, description) + instructions
├── references/       # Optional — reference docs loaded as needed
└── scripts/          # Optional — executable scripts the skill can run
```

## Available skills

| Skill | Description |
|---|---|
| [`external-link-audit`](./external-link-audit/) | Audit a website's external (outbound) links: broken links, redirected targets, insecure HTTP links, affiliate `rel="sponsored"` compliance, unsafe `target="_blank"` usage, and sitewide outbound link patterns. |
| [`internal-link-audit`](./internal-link-audit/) | Audit a website's internal linking structure: broken links, orphan pages, redirect chains, click depth, anchor text quality, and link equity distribution. |
| [`meta-data-audit`](./meta-data-audit/) | Audit a website's title tags and meta descriptions: missing, duplicate, too-long, too-short, or multiple tags, generic or boilerplate titles, and keyword stuffing. |
| [`schema-markup-audit`](./schema-markup-audit/) | Audit a website's structured data: extract JSON-LD, Microdata, and RDFa, validate against schema.org and Google rich result requirements, and find missing, invalid, or incomplete markup. |
| [`site-architecture-audit`](./site-architecture-audit/) | Audit a website's architecture and crawlability for SEO. Crawls the site and inspects robots.txt and XML sitemaps to find hostname/protocol duplication, URL structure problems, excessive crawl depth, weak directory taxonomy, blocked or conflicting crawl and index directives, and sitemap-to-crawl parity gaps. |



## Usage

Copy a skill folder into your Claude skills directory (e.g., `~/.claude/skills/` for Claude Code) or upload it where skills are supported. Claude will invoke the skill automatically when a request matches its description.
