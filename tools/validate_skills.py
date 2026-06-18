#!/usr/bin/env python3
"""Validate every Claude skill in this repository.

Checks, for each `skills/<skill-name>/` folder containing a SKILL.md:

  1. SKILL.md has YAML frontmatter delimited by `---` lines.
  2. Frontmatter has a `name:` that exactly matches the folder name.
  3. Frontmatter has a non-empty `description:` within a sane length budget.
  4. Every `scripts/<file>` and `references/<file>` path mentioned in SKILL.md
     actually exists on disk.
  5. Every `scripts/*.py` referenced (and every .py in the repo) compiles with
     `py_compile` — i.e. is syntactically valid Python.
  6. Each skill has at least one reference doc and one script (a soft warning).

Exits non-zero if any error is found, so it can gate CI.

Uses only the Python standard library.
"""

import os
import py_compile
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every skill lives under skills/<skill-name>/ with a SKILL.md.
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

DESC_MAX = 1024  # description length budget (chars); Anthropic skills stay well under this
DESC_MIN = 40

# Matches a *self-referenced* references/foo.md or scripts/bar.py in SKILL.md.
# The negative lookbehind skips paths that belong to another skill or a parent
# directory (e.g. `../sitemap-audit/scripts/collect_sitemap.py`), which a skill
# may legitimately mention without owning the file.
PATH_RE = re.compile(r"(?<![\w/.\-])((?:scripts|references)/[A-Za-z0-9._\-]+)")


def parse_frontmatter(text):
    """Return a dict of the top-level scalar keys in the YAML frontmatter, or None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    data = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s?(.*)$", line)
        if m:
            key = m.group(1)
            data[key] = m.group(2).strip()
        elif key and line.strip():
            # continuation of a folded/multi-line value
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


def find_skill_dirs():
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(path) or name.startswith("."):
            continue
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            skills.append(name)
    return skills


def validate_skill(name, errors, warnings):
    path = os.path.join(SKILLS_DIR, name)
    skill_md = os.path.join(path, "SKILL.md")
    with open(skill_md, encoding="utf-8") as f:
        text = f.read()

    fm = parse_frontmatter(text)
    if fm is None:
        errors.append(f"{name}/SKILL.md: missing or unterminated YAML frontmatter")
        return

    fm_name = fm.get("name", "").strip().strip("\"'")
    if not fm_name:
        errors.append(f"{name}/SKILL.md: frontmatter missing `name:`")
    elif fm_name != name:
        errors.append(f"{name}/SKILL.md: name `{fm_name}` does not match folder `{name}`")

    desc = fm.get("description", "").strip().strip("\"'")
    if not desc:
        errors.append(f"{name}/SKILL.md: frontmatter missing `description:`")
    else:
        if len(desc) < DESC_MIN:
            warnings.append(f"{name}/SKILL.md: description is very short ({len(desc)} chars)")
        if len(desc) > DESC_MAX:
            errors.append(f"{name}/SKILL.md: description too long ({len(desc)} > {DESC_MAX} chars)")

    # Referenced files must exist.
    referenced = set(PATH_RE.findall(text))
    for rel in sorted(referenced):
        if not os.path.isfile(os.path.join(path, rel)):
            errors.append(f"{name}/SKILL.md: references `{rel}` but {name}/{rel} does not exist")

    # Soft structural expectations.
    if not os.path.isdir(os.path.join(path, "scripts")) or not any(
        f.endswith(".py") for f in os.listdir(os.path.join(path, "scripts"))
        if os.path.isdir(os.path.join(path, "scripts"))
    ):
        warnings.append(f"{name}: no scripts/*.py found")
    if not os.path.isdir(os.path.join(path, "references")):
        warnings.append(f"{name}: no references/ folder found")


def check_shared_scripts(skills, errors):
    """Each skill ships its own copy of md_to_docx.py (skills are self-contained,
    and the installer copies folders individually). Assert every copy is
    byte-identical to the canonical tools/md_to_docx.py so they never drift."""
    canonical = os.path.join(REPO_ROOT, "tools", "md_to_docx.py")
    if not os.path.isfile(canonical):
        errors.append("tools/md_to_docx.py is missing (canonical .docx converter)")
        return
    with open(canonical, "rb") as f:
        want = f.read()
    for name in skills:
        copy = os.path.join(SKILLS_DIR, name, "scripts", "md_to_docx.py")
        if not os.path.isfile(copy):
            errors.append(f"{name}: missing scripts/md_to_docx.py (run tools/sync_shared.py)")
            continue
        with open(copy, "rb") as f:
            if f.read() != want:
                errors.append(
                    f"{name}/scripts/md_to_docx.py differs from tools/md_to_docx.py "
                    "(run tools/sync_shared.py)"
                )


def compile_all_python(errors):
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", ".github", ".idea", "node_modules"}]
        for fn in files:
            if fn.endswith(".py"):
                full = os.path.join(root, fn)
                try:
                    py_compile.compile(full, doraise=True)
                except py_compile.PyCompileError as e:
                    rel = os.path.relpath(full, REPO_ROOT)
                    errors.append(f"{rel}: Python syntax error: {e.msg.strip()}")


def main():
    errors = []
    warnings = []

    skills = find_skill_dirs()
    if not skills:
        print("No skills found.", file=sys.stderr)
        sys.exit(1)

    for name in skills:
        validate_skill(name, errors, warnings)

    check_shared_scripts(skills, errors)
    compile_all_python(errors)

    print(f"Validated {len(skills)} skill(s): {', '.join(skills)}\n")

    for w in warnings:
        print(f"  warning: {w}")
    for e in errors:
        print(f"  ERROR:   {e}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). FAILED.")
        sys.exit(1)
    print(f"\nAll checks passed ({len(warnings)} warning(s)).")


if __name__ == "__main__":
    main()
