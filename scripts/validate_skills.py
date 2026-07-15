#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def parse_skill(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not frontmatter:
        raise ValueError(f"{path}: missing frontmatter")
    name = re.search(r"^name:\s*([^\n]+)$", frontmatter.group(1), re.M)
    description = re.search(r"^description:\s*>-\n((?:  .*\n?)+)", frontmatter.group(1), re.M)
    if not name or not description:
        raise ValueError(f"{path}: missing name/description")
    return {
        "name": name.group(1).strip(),
        "description": " ".join(line.strip() for line in description.group(1).splitlines()),
        "text": text,
    }


def section(text: str, heading: str) -> str:
    match = re.search(r"^" + re.escape(heading) + r"\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def overlap_tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "or", "to", "a", "an", "of", "for", "with", "when",
        "use", "do", "not", "git", "repository", "branch", "branches", "state",
        "exact", "intended", "local", "remote",
    }
    return {
        token for token in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
        if token not in stop
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


errors: list[str] = []
catalog = load_json("skills/catalog.json")
plugin = load_json(".claude-plugin/plugin.json")
names = [item["name"] for item in catalog["skills"]]
name_set = set(names)
name_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

if len(names) != len(name_set):
    errors.append("duplicate catalog skill names")
for name in names:
    if not name_pattern.fullmatch(name):
        errors.append(f"invalid skill name: {name}")

if catalog.get("package_version") != plugin.get("version"):
    errors.append("catalog/plugin version mismatch")
if catalog.get("base_release") != {
    "tag": "v1.0.0",
    "commit": "1d513f5b29332c406c33705c42ccec6dfaf86e3c",
}:
    errors.append("base release identity mismatch")

# Catalog tiers, filesystem, plugin, and README are one routing inventory.
tier_names: list[str] = []
for tier in ("core", "optional"):
    listed = catalog.get("tiers", {}).get(tier, {}).get("skills", [])
    actual = [item["name"] for item in catalog["skills"] if item["tier"] == tier]
    tier_names.extend(listed)
    if set(listed) != set(actual):
        errors.append(f"{tier} tier/catalog mismatch")
if len(tier_names) != len(set(tier_names)) or set(tier_names) != name_set:
    errors.append("tier lists must partition catalog exactly")

for item in catalog["skills"]:
    if item.get("path") != f"skills/{item['name']}":
        errors.append(f"{item['name']}: noncanonical catalog path")
    if not item.get("summary", "").strip():
        errors.append(f"{item['name']}: missing catalog summary")

disk = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
expected_plugin_paths = [f"./skills/{name}" for name in names]
plugin_paths = plugin.get("skills", [])
plugin_names = {Path(path).name for path in plugin_paths}
readme = (ROOT / "README.md").read_text(encoding="utf-8")
readme_names = set(re.findall(r"\[`([a-z0-9-]+)`\]\(skills/[^)]+/SKILL\.md\)", readme))
for label, found in (("disk", disk), ("plugin", plugin_names), ("README", readme_names)):
    if found != name_set:
        errors.append(f"{label}/catalog mismatch: extra={sorted(found-name_set)} missing={sorted(name_set-found)}")
if plugin_paths != expected_plugin_paths:
    errors.append("plugin skill paths/order must exactly match the catalog")

version = catalog.get("package_version", "")
release_date = catalog.get("release_date", "")
compatibility = catalog.get("compatibility", {})
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
if f"## {version} - {release_date}" not in changelog:
    errors.append("changelog version/date mismatch")
compat_doc = (ROOT / "docs/COMPATIBILITY.md").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
python_compat = compatibility.get("python", {})
ci_compat = compatibility.get("ci", {})
client_compat = compatibility.get("packaging_clients", {})
required_doc_values = [python_compat.get("minimum"), *python_compat.get("ci_matrix", []), ci_compat.get("os")]
for value in filter(None, required_doc_values):
    if str(value) not in compat_doc:
        errors.append(f"compatibility documentation missing {value}")
required_workflow_values = [*python_compat.get("ci_matrix", []), ci_compat.get("os")]
for group in (client_compat.get("blocking", {}), client_compat.get("forward_probe", {})):
    required_workflow_values.extend(group.get(key) for key in ("node", "skills_cli", "claude_code"))
for value in filter(None, required_workflow_values):
    if str(value) not in workflow:
        errors.append(f"validation workflow missing catalog compatibility value {value}")

required_sections = [
    "## Objective", "## Use When", "## Do Not Use / Route Elsewhere",
    "## Required Evidence", "## Action Boundaries", "## Workflow",
    "## Verification", "## Output Contract",
]
all_refs: set[Path] = set()
skills: dict[str, dict[str, object]] = {}

for name in names:
    path = ROOT / "skills" / name / "SKILL.md"
    try:
        parsed = parse_skill(path)
    except ValueError as exc:
        errors.append(str(exc))
        continue

    if parsed["name"] != name:
        errors.append(f"{path}: frontmatter name mismatch")
    if not 1 <= len(parsed["description"]) <= 1024:
        errors.append(f"{path}: description length {len(parsed['description'])}")
    if "Use" not in parsed["description"] or "Do not use" not in parsed["description"]:
        errors.append(f"{path}: description lacks positive/negative routing")
    for heading in required_sections:
        if heading not in parsed["text"]:
            errors.append(f"{path}: missing {heading}")
    if len(parsed["text"].splitlines()) > 500:
        errors.append(f"{path}: exceeds 500-line heuristic")

    reference_contract = section(parsed["text"], "## Reference Trigger") + section(parsed["text"], "## Reference Triggers")
    refs = re.findall(r"`(references/[^`]+\.md)`", reference_contract)
    if len(refs) != len(set(refs)):
        errors.append(f"{path}: duplicate reference trigger")
    for rel in refs:
        ref = path.parent / rel
        all_refs.add(ref.resolve())
        if not ref.is_file():
            errors.append(f"{path}: missing {rel}")
        elif re.search(r"`references/[^`]+\.md`", ref.read_text(encoding="utf-8")):
            errors.append(f"{ref}: reference-to-reference chain")

    script_contract = section(parsed["text"], "## Script Trigger") + section(parsed["text"], "## Script Triggers")
    script_mentions = set(re.findall(r"`(scripts/[^`]+)`", script_contract))
    for script in sorted(path.parent.glob("scripts/*")):
        if not script.is_file() or script.name.startswith("."):
            continue
        rel = f"scripts/{script.name}"
        if rel not in script_mentions:
            errors.append(f"{path}: bundled script lacks exact trigger `{rel}`")
    for rel in script_mentions:
        script = path.parent / rel
        if not script.is_file():
            errors.append(f"{path}: missing {rel}")

    objective = section(parsed["text"], "## Objective")
    use_when = section(parsed["text"], "## Use When")
    skills[name] = {
        "objective": re.sub(r"\s+", " ", objective.strip()).casefold(),
        "tokens": overlap_tokens(parsed["description"] + " " + objective + " " + use_when),
        "nonuse": section(parsed["text"], "## Do Not Use / Route Elsewhere"),
    }

for ref in (ROOT / "skills").glob("*/references/*.md"):
    if ref.resolve() not in all_refs:
        errors.append(f"{ref}: orphan reference without direct SKILL trigger")

# Routing and failure fixtures must exactly cover the current catalog.
routing_doc = load_json("tests/routing.json")
scenario_doc = load_json("tests/scenarios.json")
routing = routing_doc["cases"]
scenarios = scenario_doc["scenarios"]
if scenario_doc.get("kind") != "static-contract-scenarios":
    errors.append("tests/scenarios.json must identify static contract scenarios")
for label, rows in (("routing", routing), ("scenario", scenarios)):
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate {label} ids")
    found = {row["skill"] for row in rows}
    if found != name_set:
        errors.append(f"{label}/catalog mismatch: extra={sorted(found-name_set)} missing={sorted(name_set-found)}")

by_skill: dict[str, list[dict]] = defaultdict(list)
for row in routing:
    by_skill[row["skill"]].append(row)
for name in names:
    positive = sum(row["expect"] == "route" for row in by_skill[name])
    negative = sum(row["expect"] == "do-not-route" for row in by_skill[name])
    if positive < 3 or negative < 2:
        errors.append(f"{name}: routing coverage {positive} positive/{negative} negative")

categories: dict[str, set[str]] = defaultdict(set)
for row in scenarios:
    categories[row["skill"]].add(row["category"])
    prompt = row.get("prompt", "").strip()
    assertions = row.get("assertions")
    if len(prompt) < 80 or prompt.startswith("Perform the "):
        errors.append(f"{row.get('id')}: scenario prompt is generic or underspecified")
    if not isinstance(assertions, list) or len(assertions) < 3 or len(assertions) != len(set(assertions)):
        errors.append(f"{row.get('id')}: scenario assertions must contain at least three unique checks")
required_categories = {"stale-state", "partial-failure", "prompt-injection"}
for name in names:
    if not required_categories <= categories[name]:
        errors.append(f"{name}: missing scenario categories {sorted(required_categories-categories[name])}")

for prompt, count in Counter(row["prompt"].strip().casefold() for row in routing + scenarios).items():
    if count > 1:
        errors.append(f"duplicate prompt text: {prompt[:80]}")

# Known intersections require reciprocal routing; lexical similarity flags unbounded new overlaps.
required_reciprocal = {
    ("recover-lost-work", "repair-repository-integrity"),
    ("repair-repository-integrity", "setup-repository"),
    ("optimize-large-repository", "repair-repository-integrity"),
    ("manage-large-files", "repair-repository-integrity"),
    ("edit-commit-history", "manage-stacked-branches"),
    ("integrate-branches", "manage-stacked-branches"),
    ("manage-stacked-branches", "sync-branches"),
    ("manage-branches", "manage-stacked-branches"),
    ("preserve-work", "transplant-commits"),
    ("craft-commits", "preserve-work"),
    ("integrate-branches", "manage-submodules"),
    ("transplant-commits", "undo-changes"),
}
for left, right in required_reciprocal:
    if f"`{right}`" not in str(skills[left]["nonuse"]) or f"`{left}`" not in str(skills[right]["nonuse"]):
        errors.append(f"missing reciprocal boundary: {left}, {right}")

objectives: dict[str, str] = {}
overlap_signals = 0
for name, data in skills.items():
    objective = str(data["objective"])
    if objective in objectives:
        errors.append(f"duplicate objective: {objectives[objective]}, {name}")
    objectives[objective] = name

for left, right in combinations(sorted(skills), 2):
    score = jaccard(set(skills[left]["tokens"]), set(skills[right]["tokens"]))
    routed = f"`{right}`" in str(skills[left]["nonuse"]) or f"`{left}`" in str(skills[right]["nonuse"])
    if score >= 0.25 and not routed:
        errors.append(f"high overlap without routing boundary: {left}, {right} ({score:.2f})")
    overlap_signals += score >= 0.10

# Tracked Markdown links must resolve within the source tree; external URLs are out of scope.
for md in ROOT.rglob("*.md"):
    if ".git" in md.parts or "dist" in md.parts:
        continue
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        rel = target.split("#", 1)[0]
        if not rel:
            continue
        resolved = (md.parent / rel).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{md}: internal link escapes package root {target}")
            continue
        if not resolved.exists():
            errors.append(f"{md}: broken internal link {target}")

if errors:
    print("\n".join("ERROR: " + error for error in errors))
    raise SystemExit(1)

skill_scripts = sum(1 for script in (ROOT / "skills").glob("*/scripts/*") if script.is_file())
print(
    f"PASS validate_skills: {len(names)} skills, {len(all_refs)} references, "
    f"{skill_scripts} skill scripts, {len(routing)} routing cases, "
    f"{len(scenarios)} static contract scenarios, {overlap_signals} overlap review signals"
)
