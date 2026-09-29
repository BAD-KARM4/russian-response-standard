#!/usr/bin/env python3
"""Validate Russian Response Standard repository consistency."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> None:
    raise SystemExit(message)


def read(path: str) -> str:
    file_path = ROOT / path
    if not file_path.is_file():
        fail(f"Missing required file: {path}")
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as error:
        fail(f"Cannot read {path}: {error}")


REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "agents/openai.yaml",
    "assets/icon.svg",
    "tests/regression.md",
    "scripts/validate-package.py",
    "scripts/build-plugin.py",
    ".github/workflows/release.yml",
    ".github/workflows/validate.yml",
]

for required in REQUIRED_FILES:
    if not (ROOT / required).is_file():
        fail(f"Missing required file: {required}")

skill = read("SKILL.md")
readme = read("README.md")
changelog = read("CHANGELOG.md")
openai = read("agents/openai.yaml")
release_workflow = read(".github/workflows/release.yml")

if "\t" in skill:
    fail("SKILL.md must not contain tab characters")

frontmatter_match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
if frontmatter_match is None:
    fail("SKILL.md must begin with YAML frontmatter")

frontmatter = frontmatter_match.group(1)
frontmatter_lines = frontmatter.splitlines()

if not frontmatter_lines or frontmatter_lines[0] != "name: russian-response-standard":
    fail("SKILL.md frontmatter must start with name: russian-response-standard")

try:
    description_index = frontmatter_lines.index("description: >-")
except ValueError:
    fail("SKILL.md description must use the folded YAML scalar: description: >-")

if description_index != 1:
    fail("SKILL.md description must immediately follow name")

description_lines = frontmatter_lines[description_index + 1 :]
if not description_lines:
    fail("SKILL.md description must not be empty")
if any(line and not line.startswith("  ") for line in description_lines):
    fail("Every SKILL.md description line must be indented by two spaces")

version_matches = re.findall(r"(?m)^Версия: (v\d+\.\d+\.\d+)$", skill)
if len(version_matches) != 1:
    fail(f"SKILL.md must contain exactly one semantic version, found: {version_matches}")
version = version_matches[0]

changelog_versions = re.findall(r"(?m)^## (v\d+\.\d+\.\d+)$", changelog)
if not changelog_versions:
    fail("CHANGELOG.md must contain at least one version")
if changelog_versions[0] != version:
    fail(
        f"Current SKILL.md version {version} does not match first CHANGELOG.md version "
        f"{changelog_versions[0]}"
    )
if len(changelog_versions) != len(set(changelog_versions)):
    fail("CHANGELOG.md contains duplicate version headings")

current_section = re.search(
    rf"(?ms)^## {re.escape(version)}\n\n(.+?)(?=^## v\d+\.\d+\.\d+\n|\Z)",
    changelog,
)
if current_section is None or not current_section.group(1).strip():
    fail(f"CHANGELOG.md section for {version} is empty")

for character, name in (("\u2014", "em dash U+2014"), ("\u2013", "en dash U+2013")):
    if character in skill:
        fail(f"SKILL.md contains forbidden {name}")

fence = re.escape(chr(96) * 3)
prose_without_fences = re.sub(
    rf"(?ms)^{fence}.*?^{fence}\s*",
    "",
    skill,
)
if chr(96) in prose_without_fences:
    fail("SKILL.md contains inline-code backticks outside fenced code blocks")

required_openai_fragments = [
    'display_name: "Russian Response Standard"',
    'icon_small: "./assets/icon.svg"',
    'icon_large: "./assets/icon.svg"',
    '$russian-response-standard',
]
for fragment in required_openai_fragments:
    if fragment not in openai:
        fail(f"agents/openai.yaml is missing required fragment: {fragment}")

for link in ("[CHANGELOG.md](CHANGELOG.md)", "[AGENTS.md](AGENTS.md)"):
    if link not in readme:
        fail(f"README.md is missing repository link: {link}")

workflow_fragments = [
    "python3 scripts/validate-package.py",
    "python3 scripts/build-plugin.py",
    "--notes-file release-notes.md",
    "Validate installable ZIP",
    '"$PLUGIN_ARCHIVE"',
]
for fragment in workflow_fragments:
    if fragment not in release_workflow:
        fail(f"release workflow is missing required protection: {fragment}")

with tempfile.TemporaryDirectory() as directory:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build-plugin.py"), str(Path(directory) / "plugin.zip")],
        check=True,
    )

print(f"Russian Response Standard {version} package is valid")
