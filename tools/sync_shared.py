#!/usr/bin/env python3
"""Copy shared scripts into every skill so each skill stays self-contained.

The installer (bin/cli.js) copies skill folders individually, so a script that
several skills rely on cannot live only in tools/ — it must exist inside each
skill's scripts/ folder. tools/ holds the canonical copy; this script stamps it
into every skill. tools/validate_skills.py fails CI if any copy drifts.

Currently shared: md_to_docx.py (Markdown report -> Word .docx converter).

Usage:
    python3 tools/sync_shared.py          # copy into every skill
    python3 tools/sync_shared.py --check  # report drift, exit non-zero, copy nothing
"""

import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
SHARED = ["md_to_docx.py"]


def skill_dirs():
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md")):
            yield name, path


def main():
    check = "--check" in sys.argv
    drift = []
    copied = 0
    for fname in SHARED:
        canonical = os.path.join(REPO_ROOT, "tools", fname)
        with open(canonical, "rb") as f:
            want = f.read()
        for name, path in skill_dirs():
            dest = os.path.join(path, "scripts")
            os.makedirs(dest, exist_ok=True)
            dest_file = os.path.join(dest, fname)
            current = None
            if os.path.isfile(dest_file):
                with open(dest_file, "rb") as f:
                    current = f.read()
            if current == want:
                continue
            if check:
                drift.append(f"{name}/scripts/{fname}")
            else:
                shutil.copyfile(canonical, dest_file)
                copied += 1

    if check:
        if drift:
            print("Drift detected in:\n  " + "\n  ".join(drift))
            print("\nRun `python3 tools/sync_shared.py` to fix.")
            sys.exit(1)
        print("All shared scripts are in sync.")
    else:
        print(f"Synced {len(SHARED)} shared script(s); updated {copied} copy(ies).")


if __name__ == "__main__":
    main()
