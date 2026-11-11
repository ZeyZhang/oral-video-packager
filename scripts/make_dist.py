#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build both distribution packages from the skill source tree.

Outputs
  <out>/oral-video-packager.zip              WorkBuddy format (outer folder)
  <out>/oral-video-packager-skillhub.zip     SkillHub format (flat, SKILL.md at root)
  <out>/oral-video-packager-v<version>.zip   versioned copy for GitHub Release
  <out>/SHA256SUMS.txt

Only skill runtime files are packaged (SKILL.md + scripts/ assets/
references/ remotion/), so running this from either the user-level skill
directory or the GitHub repository root produces identical packages.
The version is read from SKILL.md frontmatter and cross-checked against
manifest.yaml when present; a mismatch aborts the build.
"""
import argparse
import hashlib
import io
import os
import re
import zipfile

TOP_FILES = {"SKILL.md"}
TOP_DIRS = {"scripts", "assets", "references", "remotion"}
SKIP_DIRS = {"node_modules", "out", "__pycache__", ".git", ".github",
             ".packager_work", ".remotion_work", "frames", "dist", "clips"}
SKIP_FILES = {"props.json", ".DS_Store", "Thumbs.db"}
SKIP_EXTS = (".pyc", ".pyo", ".mp4", ".mov", ".zip", ".log", ".bin")


def collect(src):
    found = []
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src).replace(os.sep, "/")
            head = rel.split("/", 1)[0]
            if "/" not in rel and head not in TOP_FILES:
                continue
            if "/" in rel and head not in TOP_DIRS:
                continue
            if name in SKIP_FILES or name.endswith(SKIP_EXTS):
                continue
            found.append((rel, full))
    if not any(rel == "SKILL.md" for rel, _ in found):
        raise SystemExit("SKILL.md not found under %s" % src)
    return sorted(found)


def read_version(src):
    text = io.open(os.path.join(src, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r"^version:\s*(\S+)", text, re.M)
    if not m:
        raise SystemExit("no version in SKILL.md frontmatter")
    version = m.group(1).strip().strip('"\'')
    man = os.path.join(src, "manifest.yaml")
    if os.path.exists(man):
        t = io.open(man, encoding="utf-8").read()
        mm = re.search(r"^version:\s*(\S+)", t, re.M)
        if mm and mm.group(1).strip() != version:
            raise SystemExit("version mismatch: SKILL.md=%s manifest.yaml=%s" %
                             (version, mm.group(1).strip()))
    return version


def write_zip(path, files, prefix):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, full in files:
            with open(full, "rb") as f:
                z.writestr(prefix + rel, f.read())
    data = open(path, "rb").read()
    print("  %-42s %7d bytes  sha256 %s" %
          (os.path.basename(path), len(data), hashlib.sha256(data).hexdigest()))
    return os.path.basename(path), hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".", help="skill source root (contains SKILL.md)")
    ap.add_argument("--out", default="dist", help="output directory")
    args = ap.parse_args()
    src, out = os.path.abspath(args.src), os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    version = read_version(src)
    files = collect(src)
    print("source:  %s" % src)
    print("version: %s   (%d files)" % (version, len(files)))
    sums = []
    sums.append(write_zip(os.path.join(out, "oral-video-packager.zip"),
                          files, "oral-video-packager/"))
    sums.append(write_zip(os.path.join(out, "oral-video-packager-skillhub.zip"),
                          files, ""))
    sums.append(write_zip(os.path.join(out, "oral-video-packager-v%s.zip" % version),
                          files, "oral-video-packager/"))
    with io.open(os.path.join(out, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        for name, digest in sums:
            f.write("%s  %s\n" % (digest, name))
    print("  SHA256SUMS.txt written")
    print("\nSkillHub package has SKILL.md at root? %s" %
          ("SKILL.md" in zipfile.ZipFile(
              os.path.join(out, "oral-video-packager-skillhub.zip")).namelist()))


if __name__ == "__main__":
    main()
