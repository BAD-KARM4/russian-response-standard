#!/usr/bin/env python3
"""Build and verify a skills-only plugin from the repository skill."""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "russian-response-standard"
WORK_DESCRIPTION = "Всегда применяй этот навык ко всем ответам на русском языке в Work."
CHAT_DESCRIPTION = "Всегда применяй этот навык ко всем ответам на русском языке в Chat и Work."
WORK_PROMPT = "Используй $russian-response-standard, чтобы"
CHAT_PROMPT = "Используй навык russian-response-standard, чтобы"


def replace_once(content: str, before: str, after: str, filename: str) -> str:
    if content.count(before) != 1:
        raise SystemExit(f"Expected exactly one source phrase in {filename}")
    return content.replace(before, after, 1)


def build(archive: Path) -> None:
    source_skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    versions = re.findall(r"(?m)^Версия: (v\d+\.\d+\.\d+)$", source_skill)
    if len(versions) != 1:
        raise SystemExit("Expected exactly one version in SKILL.md")
    version = versions[0]

    plugin_skill = replace_once(source_skill, WORK_DESCRIPTION, CHAT_DESCRIPTION, "SKILL.md")
    source_ui = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    plugin_ui = replace_once(source_ui, WORK_PROMPT, CHAT_PROMPT, "agents/openai.yaml")
    icon = (ROOT / "assets/icon.svg").read_bytes()
    manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": SKILL_NAME,
        "version": version.removeprefix("v"),
        "description": "Единый стандарт ответов на русском языке для Chat и Work.",
    }

    prefix = f"skills/{SKILL_NAME}/"
    files = {
        "plugin.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        prefix + "SKILL.md": plugin_skill.encode("utf-8"),
        prefix + "agents/openai.yaml": plugin_ui.encode("utf-8"),
        prefix + "assets/icon.svg": icon,
    }

    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            package.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(archive) as package:
        actual = {name: package.read(name) for name in package.namelist()}
        if package.testzip() is not None or actual != files:
            raise SystemExit("Plugin ZIP contents do not match the source files")
        if json.loads(actual["plugin.json"]) != manifest:
            raise SystemExit("Plugin manifest is invalid")

    print(f"Built and validated {archive} from {version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: build-plugin.py OUTPUT.zip")
    build(Path(sys.argv[1]))
