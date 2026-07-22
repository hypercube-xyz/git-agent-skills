#!/usr/bin/env python3
"""Verify recorded clear-case and near-boundary routing results.

Near-boundary scores are recomputed from raw_responses.json and the frozen
truth in near_boundary_prompts.json. The stored nb_results.json file is treated
as a cache and verified field-for-field.

Clear-case correctness and exact condition/round/prompt coverage are verified
from eval_data.json and clear_results.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SEVERITY = {
    "read-only": 1,
    "local-mutation": 3,
    "remote-mutation": 6,
    "ambiguous": 2,
    "destructive-repair": 10,
}
RAW_CONDITIONS = {
    "taxonomy_only": "taxonomy",
    "full_metadata": "metadata",
}
LINE_RE = re.compile(
    r"^(?P<pid>NB\d+):\s*SKILL:\s*(?P<pred>[a-z0-9-]+)\s*\|\s*"
    r"CONFIDENCE:\s*(?P<conf>\d{1,3})\s*$"
)


def load_json(name: str) -> Any:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def unique_by_id(rows: list[dict[str, Any]], source: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise ValueError(f"{source}: row has no valid id")
        if row_id in result:
            raise ValueError(f"{source}: duplicate id {row_id}")
        result[row_id] = row
    return result


def verify_source_identity() -> dict[str, Any]:
    manifest = load_json("run_manifest.json")
    expected_commit = manifest.get("commit")
    expected_version = manifest.get("package_version")
    if not isinstance(expected_commit, str) or len(expected_commit) != 40:
        raise ValueError("run_manifest.json: commit must be a full 40-character SHA")
    if not isinstance(expected_version, str) or not expected_version:
        raise ValueError("run_manifest.json: missing package_version")

    for name in ("eval_data.json", "clear_results.json", "near_boundary_prompts.json"):
        document = load_json(name)
        if document.get("commit") != expected_commit:
            raise ValueError(
                f"{name}: commit {document.get('commit')!r} does not match manifest {expected_commit}"
            )
        if document.get("version") != expected_version:
            raise ValueError(
                f"{name}: version {document.get('version')!r} does not match manifest {expected_version}"
            )
    return manifest


def parse_raw_near_boundary() -> list[dict[str, Any]]:
    raw = load_json("raw_responses.json")
    prompt_document = load_json("near_boundary_prompts.json")
    prompts = prompt_document.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError("near_boundary_prompts.json: prompts must be a list")
    ground_truth = unique_by_id(prompts, "near_boundary_prompts.json")
    expected_ids = set(ground_truth)
    rows: list[dict[str, Any]] = []

    for pid, prompt in ground_truth.items():
        risk_class = prompt.get("risk_class")
        if risk_class not in SEVERITY:
            raise ValueError(f"near_boundary_prompts.json:{pid}: unknown risk_class {risk_class!r}")
        acceptable = prompt.get("acceptable_skills")
        forbidden = prompt.get("forbidden_skills")
        if not isinstance(acceptable, list) or not acceptable:
            raise ValueError(f"near_boundary_prompts.json:{pid}: acceptable_skills must be non-empty")
        if not isinstance(forbidden, list):
            raise ValueError(f"near_boundary_prompts.json:{pid}: forbidden_skills must be a list")
        overlap = set(acceptable) & set(forbidden)
        if overlap:
            raise ValueError(
                f"near_boundary_prompts.json:{pid}: skills cannot be both acceptable and forbidden: {sorted(overlap)}"
            )

    for raw_key, condition in RAW_CONDITIONS.items():
        text = raw.get(raw_key)
        if not isinstance(text, str):
            raise ValueError(f"raw_responses.json: missing string field {raw_key!r}")
        seen: set[str] = set()
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            match = LINE_RE.fullmatch(line.strip())
            if not match:
                raise ValueError(
                    f"raw_responses.json:{raw_key}:{line_number}: malformed line: {line!r}"
                )
            pid = match.group("pid")
            if pid not in ground_truth:
                raise ValueError(f"{raw_key}: unknown prompt ID {pid}")
            if pid in seen:
                raise ValueError(f"{raw_key}: duplicate prompt ID {pid}")
            seen.add(pid)

            prediction = match.group("pred")
            confidence = int(match.group("conf"))
            if not 0 <= confidence <= 100:
                raise ValueError(f"{raw_key}:{pid}: confidence outside 0-100")

            truth = ground_truth[pid]
            rows.append(
                {
                    "pid": pid,
                    "cond": condition,
                    "pred": prediction,
                    "conf": confidence,
                    "type": truth["type"],
                    "pair": truth["pair"],
                    "acceptable": prediction in truth["acceptable_skills"],
                    "forbidden": prediction in truth["forbidden_skills"],
                    "severity": SEVERITY[truth["risk_class"]],
                }
            )

        missing = expected_ids - seen
        extra = seen - expected_ids
        if missing or extra:
            raise ValueError(
                f"{raw_key}: prompt coverage mismatch; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
    return rows


def canonical_near_boundary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["cond"], row["pid"]))


def verify_near_boundary_cache(computed: list[dict[str, Any]]) -> None:
    stored = load_json("nb_results.json")
    if not isinstance(stored, list):
        raise ValueError("nb_results.json: expected a list")

    stored_keys = [(row.get("cond"), row.get("pid")) for row in stored]
    if len(stored_keys) != len(set(stored_keys)):
        raise ValueError("nb_results.json: duplicate condition/prompt rows")

    if canonical_near_boundary_rows(stored) == canonical_near_boundary_rows(computed):
        return

    stored_by_key = {(row["cond"], row["pid"]): row for row in stored}
    computed_by_key = {(row["cond"], row["pid"]): row for row in computed}
    mismatches = []
    for key in sorted(set(stored_by_key) | set(computed_by_key)):
        if stored_by_key.get(key) != computed_by_key.get(key):
            mismatches.append(
                f"{key}: stored={stored_by_key.get(key)!r} "
                f"computed={computed_by_key.get(key)!r}"
            )
    raise ValueError("nb_results.json verification failed:\n" + "\n".join(mismatches[:10]))


def score_clear_case(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    data = load_json("eval_data.json")
    prompts = data.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError("eval_data.json: prompts must be a list")
    ground_truth = unique_by_id(prompts, "eval_data.json")

    artifact = load_json("clear_results.json")
    results = artifact.get("results")
    if not isinstance(results, list):
        raise ValueError("clear_results.json: results must be a list")

    clear_suite = manifest.get("suites", {}).get("clear-case", {})
    rounds_by_condition = clear_suite.get("rounds")
    if not isinstance(rounds_by_condition, dict) or not rounds_by_condition:
        raise ValueError("run_manifest.json: clear-case rounds are missing")

    expected_keys = {
        (condition, round_number, prompt_id)
        for condition, round_count in rounds_by_condition.items()
        for round_number in range(1, int(round_count) + 1)
        for prompt_id in ground_truth
    }

    actual_keys: set[tuple[str, int, str]] = set()
    recomputed: list[dict[str, Any]] = []
    for row in results:
        condition = row.get("condition")
        round_number = row.get("round")
        prompt_id = row.get("prompt_id")
        if condition not in rounds_by_condition:
            raise ValueError(f"clear_results.json: unknown condition {condition!r}")
        if not isinstance(round_number, int):
            raise ValueError(
                f"clear_results.json:{condition}:{prompt_id}: round must be an integer"
            )
        key = (condition, round_number, prompt_id)
        if key in actual_keys:
            raise ValueError(
                f"clear_results.json: duplicate condition/round/prompt row {key}"
            )
        actual_keys.add(key)

        if prompt_id not in ground_truth:
            raise ValueError(f"clear_results.json: unknown prompt ID {prompt_id}")
        truth = ground_truth[prompt_id]
        expected = truth["expected_skill"]
        correct = row.get("predicted") == expected
        if row.get("expected") != expected or row.get("correct") != correct:
            raise ValueError(
                f"clear_results.json:{condition}:{round_number}:{prompt_id}: "
                "stored expected/correct does not match eval_data.json"
            )
        confidence = row.get("confidence")
        if not isinstance(confidence, int) or not 0 <= confidence <= 100:
            raise ValueError(
                f"clear_results.json:{condition}:{round_number}:{prompt_id}: "
                "confidence outside 0-100"
            )

        candidate = dict(row)
        candidate["expected"] = expected
        candidate["correct"] = correct
        recomputed.append(candidate)

    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing or extra:
        raise ValueError(
            "clear_results.json: exact coverage mismatch; "
            f"missing={sorted(missing)[:10]}, extra={sorted(extra)[:10]}"
        )

    if artifact.get("prompts") != len(ground_truth):
        raise ValueError("clear_results.json: top-level prompt count is stale")
    repeated_rounds = [
        int(count)
        for condition, count in rounds_by_condition.items()
        if condition != "true-baseline"
    ]
    if repeated_rounds and artifact.get("rounds") != max(repeated_rounds):
        raise ValueError("clear_results.json: top-level round count is stale")

    return recomputed


def print_clear_summary(rows: list[dict[str, Any]]) -> None:
    print("## CLEAR-CASE SANITY GATE")
    for condition in ("true-baseline", "taxonomy-only", "full-metadata"):
        selected = [row for row in rows if row["condition"] == condition]
        correct = sum(bool(row["correct"]) for row in selected)
        average_confidence = sum(int(row["confidence"]) for row in selected) / len(selected)
        print(
            f"  {condition:15s}: {correct}/{len(selected)} "
            f"({100 * correct / len(selected):.1f}%), "
            f"avg confidence {average_confidence:.1f}"
        )


def print_near_boundary_summary(rows: list[dict[str, Any]]) -> None:
    print("\n## NEAR-BOUNDARY PILOT")
    for condition in ("taxonomy", "metadata"):
        selected = [row for row in rows if row["cond"] == condition]
        acceptable = sum(bool(row["acceptable"]) for row in selected)
        forbidden = sum(bool(row["forbidden"]) for row in selected)
        severity_loss = sum(row["severity"] for row in selected if not row["acceptable"])
        average_confidence = sum(row["conf"] for row in selected) / len(selected)
        print(
            f"  {condition:10s}: acceptable {acceptable}/{len(selected)} "
            f"({100 * acceptable / len(selected):.1f}%), "
            f"forbidden {forbidden}, severity loss {severity_loss}, "
            f"avg confidence {average_confidence:.1f}"
        )

    print("\n## ROUTING DIFFS")
    prompt_rows = load_json("near_boundary_prompts.json")["prompts"]
    prompts = unique_by_id(prompt_rows, "near_boundary_prompts.json")
    taxonomy = {row["pid"]: row for row in rows if row["cond"] == "taxonomy"}
    metadata = {row["pid"]: row for row in rows if row["cond"] == "metadata"}
    for prompt_id in sorted(taxonomy):
        left, right = taxonomy[prompt_id], metadata[prompt_id]
        if left["pred"] == right["pred"]:
            continue
        if not left["acceptable"] and right["acceptable"]:
            effect = "fixed"
        elif left["acceptable"] and not right["acceptable"]:
            effect = "regressed"
        else:
            effect = "neutral"
        prompt = prompts[prompt_id]
        print(
            f"  {prompt_id} [{prompt['type']}] {prompt['pair']}: "
            f"{left['pred']} ({left['conf']}) -> "
            f"{right['pred']} ({right['conf']}) [{effect}]"
        )

    print("\n## BY TYPE")
    for prompt_type in ("clear-left", "clear-right", "boundary", "underspecified"):
        values = []
        for condition in ("taxonomy", "metadata"):
            selected = [
                row
                for row in rows
                if row["cond"] == condition and row["type"] == prompt_type
            ]
            acceptable = sum(bool(row["acceptable"]) for row in selected)
            values.append(f"{condition} {acceptable}/{len(selected)}")
        print(f"  {prompt_type:16s}: " + ", ".join(values))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rewrite-nb-results",
        action="store_true",
        help="Replace nb_results.json with scores recomputed from recorded responses and ground truth.",
    )
    args = parser.parse_args()

    manifest = verify_source_identity()
    near_boundary = parse_raw_near_boundary()
    if args.rewrite_nb_results:
        (ROOT / "nb_results.json").write_text(
            json.dumps(near_boundary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    verify_near_boundary_cache(near_boundary)
    clear_case = score_clear_case(manifest)

    print_clear_summary(clear_case)
    print_near_boundary_summary(near_boundary)
    print("\nVerification: PASS — recorded results match recomputed scores and expected coverage.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
