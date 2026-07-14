#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LINK_RE = re.compile(r"`references/([^`]+)`")
REQUIRED_SIGNALS = {
    "objective": ["## Objective"],
    "routing-positive": ["## Use When"],
    "routing-negative": ["## Do Not Use / Route Elsewhere"],
    "evidence": ["## Required Evidence"],
    "decision": ["## Decision Rules"],
    "action-boundary": ["## Action Boundaries", "Desired postcondition", "Protected state", "Prohibited effects"],
    "workflow": ["## Workflow"],
    "stop": ["## Stop and Reassess"],
    "verification": ["## Verification"],
    "output": ["## Output Contract"],
    "reference-trigger": ["## Reference Trigger"],
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def parse_frontmatter(path: Path, text: str, errors: list[str]) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(errors, f"{path}: missing YAML frontmatter")
        return {}
    block = match.group(1).splitlines()
    data: dict[str, str] = {}
    i = 0
    while i < len(block):
        line = block[i]
        if not line.strip():
            i += 1
            continue
        if ":" not in line:
            fail(errors, f"{path}: malformed frontmatter line: {line!r}")
            i += 1
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value == ">-":
            i += 1
            folded = []
            while i < len(block) and (block[i].startswith("  ") or not block[i].strip()):
                if block[i].strip():
                    folded.append(block[i].strip())
                i += 1
            data[key] = " ".join(folded)
            continue
        data[key] = value.strip('"\'')
        i += 1
    return data


def main() -> int:
    errors: list[str] = []
    skill_files = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if not skill_files:
        fail(errors, "no skills/*/SKILL.md files found")

    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    manifest_paths = manifest.get("skills")
    if not isinstance(manifest_paths, list) or not manifest_paths:
        fail(errors, ".claude-plugin/plugin.json: skills must be a non-empty array")
        manifest_paths = []

    manifest_names: list[str] = []
    for value in manifest_paths:
        if not isinstance(value, str) or not value.startswith("./skills/"):
            fail(errors, f"plugin manifest: invalid skill path {value!r}")
            continue
        p = ROOT / value[2:]
        if not (p / "SKILL.md").is_file():
            fail(errors, f"plugin manifest: missing {p / 'SKILL.md'}")
        manifest_names.append(Path(value).name)

    filesystem_names = [p.parent.name for p in skill_files]
    filesystem_set = set(filesystem_names)
    if len(manifest_names) != len(set(manifest_names)):
        fail(errors, "plugin manifest contains duplicate skill paths")
    if set(manifest_names) != filesystem_set:
        fail(errors, "plugin manifest catalog does not exactly match skills/* directories")

    catalog = json.loads((ROOT / "skills" / "catalog.json").read_text())
    catalog_names = [item.get("name") for item in catalog]
    if catalog_names != manifest_names:
        fail(errors, "skills/catalog.json order/catalog does not exactly match plugin manifest")

    readme = (ROOT / "README.md").read_text()
    readme_names = re.findall(r"\[`([a-z0-9-]+)`\]\(skills/\1/SKILL\.md\)", readme)
    if readme_names != manifest_names:
        fail(errors, "README skill catalog order does not exactly match plugin manifest")

    all_references: set[Path] = set()
    linked_references: set[Path] = set()

    for path in skill_files:
        text = path.read_text()
        directory = path.parent.name
        fm = parse_frontmatter(path, text, errors)
        name = fm.get("name", "")
        desc = fm.get("description", "")

        if name != directory:
            fail(errors, f"{path}: frontmatter name {name!r} must equal directory {directory!r}")
        if not NAME_RE.fullmatch(name):
            fail(errors, f"{path}: invalid portable skill name {name!r}")
        if not (1 <= len(desc) <= 1024):
            fail(errors, f"{path}: description length must be 1..1024")
        if "Use " not in desc and "Use when" not in desc:
            fail(errors, f"{path}: description lacks positive activation language")
        if "Do not use" not in desc:
            fail(errors, f"{path}: description lacks a negative routing boundary")

        for label, signals in REQUIRED_SIGNALS.items():
            if not all(signal in text for signal in signals):
                fail(errors, f"{path}: missing semantic contract element {label}")

        if len(text.splitlines()) > 500:
            fail(errors, f"{path}: exceeds 500-line context heuristic")
        if len(text.split()) > 5000:
            fail(errors, f"{path}: exceeds 5,000-word conservative context budget")

        refs = set(LINK_RE.findall(text))
        ref_dir = path.parent / "references"
        present = set(ref_dir.glob("*.md")) if ref_dir.exists() else set()
        all_references |= present
        for rel in refs:
            ref = ref_dir / rel
            linked_references.add(ref)
            if not ref.is_file():
                fail(errors, f"{path}: missing linked reference {ref}")
            trigger_phrase = f"Read `references/{rel}` when "
            if trigger_phrase not in text:
                fail(errors, f"{path}: reference lacks explicit loading trigger for {rel}")

        for ref in present:
            rtext = ref.read_text()
            if re.search(r"(?:references/|\.{1,2}/)[^\s`)]+\.md", rtext):
                fail(errors, f"{ref}: reference-to-reference chain is prohibited")

    unused = sorted(all_references - linked_references)
    for ref in unused:
        fail(errors, f"{ref}: reference exists but is not directly linked from SKILL.md")

    routing = json.loads((ROOT / "tests" / "routing.json").read_text())
    scenarios = json.loads((ROOT / "tests" / "scenarios.json").read_text())
    known = set(filesystem_names)
    for entry in routing:
        if entry.get("skill") not in known:
            fail(errors, f"routing fixture references unknown skill: {entry}")
        if not isinstance(entry.get("should_trigger"), bool) or not str(entry.get("prompt", "")).strip():
            fail(errors, f"invalid routing fixture: {entry}")
    for entry in scenarios:
        if entry.get("skill") not in known or not str(entry.get("scenario", "")).strip() or not str(entry.get("expected_behavior", "")).strip():
            fail(errors, f"invalid scenario fixture: {entry}")

    helper = ROOT / "skills" / "manage-remotes" / "scripts" / "inspect_remotes.py"
    if not helper.is_file() or not (helper.stat().st_mode & 0o111):
        fail(errors, "manage-remotes redaction helper must exist and be executable")

    if errors:
        print("FAIL:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: {len(skill_files)} skills")
    print("PASS: plugin, filesystem, catalog.json, frontmatter, and README catalogs")
    print(f"PASS: {len(routing)} routing fixtures")
    print(f"PASS: {len(scenarios)} boundary/failure scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
