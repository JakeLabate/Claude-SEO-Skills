#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const PKG_ROOT = path.join(__dirname, "..");

// The list of skills shipped with this package. Each entry is a top-level
// folder containing a SKILL.md (plus optional references/ and scripts/).
const SKILLS = [
  "canonical-tag-audit",
  "content-quality-audit",
  "core-web-vitals-audit",
  "external-link-audit",
  "full-seo-audit",
  "heading-structure-audit",
  "image-seo-audit",
  "internal-link-audit",
  "keyword-cannibalization-audit",
  "llms-txt-audit",
  "meta-data-audit",
  "mixed-content-audit",
  "open-graph-audit",
  "pagination-audit",
  "redirect-audit",
  "robots-txt-audit",
  "schema-markup-audit",
  "site-architecture-audit",
  "sitemap-audit",
  "soft-404-audit",
];

function readDescription(skill) {
  const skillMd = path.join(PKG_ROOT, skill, "SKILL.md");
  try {
    const text = fs.readFileSync(skillMd, "utf8");
    const match = text.match(/^description:\s*(.+?)\s*$/m);
    if (match) {
      let desc = match[1].replace(/^["']|["']$/g, "");
      if (desc.length > 100) desc = desc.slice(0, 97) + "...";
      return desc;
    }
  } catch {
    /* ignore */
  }
  return "";
}

function resolveTargetDir(args) {
  const dirFlag = getFlagValue(args, "--dir");
  if (dirFlag) return path.resolve(dirFlag);

  if (args.includes("--project") || args.includes("-p")) {
    return path.resolve(process.cwd(), ".claude", "skills");
  }
  // Default: the user's global Claude skills directory.
  return path.join(os.homedir(), ".claude", "skills");
}

function getFlagValue(args, name) {
  const eq = args.find((a) => a.startsWith(name + "="));
  if (eq) return eq.slice(name.length + 1);
  const idx = args.indexOf(name);
  if (idx !== -1 && args[idx + 1] && !args[idx + 1].startsWith("-")) {
    return args[idx + 1];
  }
  return null;
}

function listSkills() {
  console.log("\nclaude-seo-skills — available skills:\n");
  for (const skill of SKILLS) {
    const desc = readDescription(skill);
    console.log("  \x1b[1m" + skill + "\x1b[0m");
    if (desc) console.log("    " + desc);
  }
  console.log(
    "\nInstall all:        npx claude-seo-skills install" +
      "\nInstall one:        npx claude-seo-skills install sitemap-audit" +
      "\nInto a project:     npx claude-seo-skills install --project\n"
  );
}

function copySkill(skill, targetDir, force) {
  const src = path.join(PKG_ROOT, skill);
  if (!fs.existsSync(src)) {
    console.error("  \x1b[31m✗\x1b[0m " + skill + " — not found in package");
    return false;
  }
  const dest = path.join(targetDir, skill);
  if (fs.existsSync(dest) && !force) {
    console.log(
      "  \x1b[33m•\x1b[0m " + skill + " — already exists (use --force to overwrite)"
    );
    return false;
  }
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(src, dest, { recursive: true });
  console.log("  \x1b[32m✓\x1b[0m " + skill);
  return true;
}

function install(args) {
  const force = args.includes("--force") || args.includes("-f");
  const targetDir = resolveTargetDir(args);

  const named = args.filter((a) => !a.startsWith("-"));
  // Drop a leading "--dir <value>" positional if it was consumed as a flag value.
  const dirVal = getFlagValue(args, "--dir");
  const requested = named.filter((a) => a !== dirVal);

  let toInstall;
  if (requested.length === 0) {
    toInstall = SKILLS;
  } else {
    toInstall = [];
    for (const name of requested) {
      if (SKILLS.includes(name)) {
        toInstall.push(name);
      } else {
        console.error('\x1b[31mUnknown skill: "' + name + '"\x1b[0m');
        console.error("Run `npx claude-seo-skills list` to see available skills.");
        process.exit(1);
      }
    }
  }

  fs.mkdirSync(targetDir, { recursive: true });
  console.log("\nInstalling into: " + targetDir + "\n");

  let installed = 0;
  for (const skill of toInstall) {
    if (copySkill(skill, targetDir, force)) installed++;
  }

  console.log(
    "\nDone. " + installed + " of " + toInstall.length + " skill(s) installed.\n"
  );
}

function printHelp() {
  console.log(
    [
      "",
      "claude-seo-skills — install Claude Agent Skills for SEO audits.",
      "",
      "Usage:",
      "  npx claude-seo-skills <command> [skills...] [options]",
      "",
      "Commands:",
      "  install [skills...]   Install all skills, or only the named ones.",
      "  list                  List available skills and their descriptions.",
      "  help                  Show this help.",
      "",
      "Options:",
      "  --project, -p         Install into ./.claude/skills (this project)",
      "                        instead of the global ~/.claude/skills.",
      "  --dir <path>          Install into a custom directory.",
      "  --force, -f           Overwrite skills that already exist.",
      "",
      "Examples:",
      "  npx claude-seo-skills install",
      "  npx claude-seo-skills install sitemap-audit robots-txt-audit",
      "  npx claude-seo-skills install --project",
      "  npx claude-seo-skills install --dir ~/my-skills --force",
      "",
    ].join("\n")
  );
}

function main() {
  const argv = process.argv.slice(2);
  const command = argv[0];
  const rest = argv.slice(1);

  switch (command) {
    case "install":
    case "add":
      install(rest);
      break;
    case "list":
    case "ls":
      listSkills();
      break;
    case undefined:
    case "help":
    case "--help":
    case "-h":
      printHelp();
      break;
    default:
      console.error('Unknown command: "' + command + '"\n');
      printHelp();
      process.exit(1);
  }
}

main();
