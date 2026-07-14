#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    routing = json.loads((ROOT / "tests" / "routing.json").read_text())
    scenarios = json.loads((ROOT / "tests" / "scenarios.json").read_text())
    catalog = json.loads((ROOT / "skills" / "catalog.json").read_text())
    skills = [item["name"] for item in catalog]

    errors: list[str] = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in routing:
        grouped[row["skill"]].append(row)

    prompts = [row["prompt"].strip().casefold() for row in routing]
    duplicate_prompts = [p for p, count in Counter(prompts).items() if count > 1]
    if duplicate_prompts:
        errors.append(f"duplicate routing prompts: {duplicate_prompts}")

    for skill in skills:
        rows = grouped[skill]
        positives = [r for r in rows if r["should_trigger"]]
        negatives = [r for r in rows if not r["should_trigger"]]
        if len(positives) < 3:
            errors.append(f"{skill}: requires at least 3 positive routing prompts")
        if len(negatives) < 2:
            errors.append(f"{skill}: requires at least 2 negative routing prompts")
        if all(re.match(r"(?i)^(git |create |run |use |execute )", r["prompt"].strip()) for r in positives):
            errors.append(f"{skill}: positives are all command-led; add symptom/outcome phrasing")

    if not any(re.search(r"[\u0E00-\u0E7F]", row["prompt"]) for row in routing):
        errors.append("routing fixtures contain no Thai-language prompt")

    scenario_group: dict[str, list[dict]] = defaultdict(list)
    for row in scenarios:
        scenario_group[row["skill"]].append(row)
    scenario_text = [f'{r["scenario"]}|{r["expected_behavior"]}'.casefold() for r in scenarios]
    if len(scenario_text) != len(set(scenario_text)):
        errors.append("duplicate boundary/failure scenario")
    for skill in skills:
        if len(scenario_group[skill]) < 2:
            errors.append(f"{skill}: requires at least 2 boundary/failure scenarios")

    # Cross-skill routing sanity: every negative prompt should be a plausible positive elsewhere
    # or clearly describe an unsupported external operation.
    positive_words = " ".join(r["prompt"].casefold() for r in routing if r["should_trigger"])
    for row in routing:
        if row["should_trigger"]:
            continue
        prompt = row["prompt"].casefold()
        content_words = [w for w in re.findall(r"[a-z]{5,}", prompt) if w not in {"without", "current", "branch", "changes"}]
        if content_words and not any(word in positive_words for word in content_words):
            # Informational only; do not fail specialized near-miss wording.
            pass

    if errors:
        print("FAIL:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: {len(routing)} routing fixtures across {len(skills)} skills")
    print(f"PASS: {len(scenarios)} boundary/failure scenarios")
    print("PASS: positive/negative coverage, symptom phrasing, multilingual signal, and uniqueness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
