"""Validate routing/checkpoint records only; never authorize or execute Git actions."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

DECISIONS = {"evaluate", "refuse_unsafe_execution", "ask_for_evidence", "handoff"}
PHASES = {"prepared", "stopped", "verified", "unknown"}
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.IGNORECASE)


def routing_errors(document: dict, owners: set[str]) -> list[str]:
    errors = []
    if document.get("decision_schema_version") not in (None, 1):
        errors.append("unsupported routing decision_schema_version")
    workflow_ids = [row.get("id") for row in document.get("workflows", [])]
    if len(workflow_ids) != len(set(workflow_ids)):
        errors.append("duplicate workflow ids")
    for row in document.get("cases", []):
        label = row.get("id", "routing case")
        if row.get("expect") not in ("route", "do-not-route"):
            errors.append(f"{label}: invalid routing expectation")
        decision = row.get("decision")
        if decision is not None or document.get("decision_schema_version") == 1:
            if not isinstance(decision, str) or decision not in DECISIONS:
                errors.append(f"{label}: invalid execution decision")
            if row.get("expect") == "do-not-route" and decision != "handoff":
                errors.append(f"{label}: an out-of-scope request must hand off, not be refused by the wrong owner")
    for row in document.get("workflows", []):
        label = row.get("id", "workflow")
        steps = row.get("steps")
        if not isinstance(steps, list) or len(steps) < 2:
            errors.append(f"{label}: workflow needs at least two steps")
            continue
        seen = set()
        for step in steps:
            owner, phase = step.get("owner"), step.get("phase")
            if not isinstance(owner, str) or owner not in owners | {"external:code-repair"}:
                errors.append(f"{label}: unknown workflow owner {owner}")
            if not isinstance(phase, str) or phase not in {"inspect", "execute", "resolve", "resume", "verify"}:
                errors.append(f"{label}: invalid workflow phase")
            if not isinstance(owner, str) or not isinstance(phase, str):
                continue
            if (owner, phase) in seen:
                errors.append(f"{label}: duplicate owner/phase; resume must not restart completed work")
            seen.add((owner, phase))
            if not isinstance(step.get("when"), str) or not step["when"].strip():
                errors.append(f"{label}: step needs its evidence/precondition")
        forbidden = row.get("forbidden_unrequested_steps", [])
        if not isinstance(forbidden, list) or any(owner not in owners for owner in forbidden):
            errors.append(f"{label}: invalid forbidden owner list")
        elif any(step.get("owner") in forbidden for step in steps):
            errors.append(f"{label}: workflow adds an explicitly unrequested step")
    return errors


def absolute(path) -> bool:
    return isinstance(path, str) and (PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute())


def checkpoint_errors(record, owners: set[str] | None = None) -> list[str]:
    required = {"schema_version", "owner", "phase", "repository", "ref", "expected_old_oid",
                "intended_new_oid", "observed_oid", "operation", "protected_paths", "protected_refs",
                "verified_effects", "unknown_effects", "next_owner", "next_action"}
    if not isinstance(record, dict):
        return ["checkpoint must be an object"]
    errors = []
    compact = type(record.get("schema_version")) is int and record["schema_version"] == 2
    minimum = {"schema_version", "owner", "phase", "repository", "next_owner", "next_action"} if compact else required
    if not minimum <= record.keys() or record.keys() - required:
        errors.append(f"checkpoint fields missing={sorted(minimum - record.keys())} extra={sorted(record.keys() - required)}")
    if type(record.get("schema_version")) is not int or record["schema_version"] not in (1, 2):
        errors.append("unsupported checkpoint schema_version")
    if compact:
        record = {"ref": None, "expected_old_oid": None, "intended_new_oid": None, "observed_oid": None,
                  "operation": {"kind": "none", "source_oid": None}, "protected_paths": {}, "protected_refs": {},
                  "verified_effects": [], "unknown_effects": [], **record}
    for field in ("owner", "next_owner"):
        value = record.get(field)
        if field == "next_owner" and value is None:
            continue
        if not isinstance(value, str) or not value or (owners is not None and value not in owners | {"external:code-repair"}):
            errors.append(f"invalid {field}")
    if not isinstance(record.get("phase"), str) or record["phase"] not in PHASES:
        errors.append("invalid checkpoint phase")
    repo = record.get("repository")
    if not isinstance(repo, dict) or set(repo) != {"worktree", "git_dir", "common_dir"} or not all(absolute(repo[key]) for key in ("git_dir", "common_dir")) or (repo["worktree"] is not None and not absolute(repo["worktree"])):
        errors.append("repository needs absolute git_dir/common_dir and absolute worktree or null for bare")
    ref = record.get("ref")
    if ref is not None and (not isinstance(ref, str) or not ref.startswith("refs/")):
        errors.append("ref must be a full ref name or null")
    for field in ("expected_old_oid", "intended_new_oid", "observed_oid"):
        value = record.get(field)
        if value is not None and (not isinstance(value, str) or not OID.fullmatch(value)):
            errors.append(f"{field} must be a complete SHA-1/SHA-256 OID or null")
    if record.get("phase") == "verified" and ref is not None:
        if record.get("observed_oid") is None:
            errors.append("verified ref needs its observed OID")
        elif record.get("intended_new_oid") is not None and record["observed_oid"] != record["intended_new_oid"]:
            errors.append("verified ref does not match intended OID")
    operation = record.get("operation")
    if not isinstance(operation, dict) or set(operation) != {"kind", "source_oid"}:
        errors.append("operation needs kind and nullable source_oid")
    elif not isinstance(operation["kind"], str) or not operation["kind"] or (operation["source_oid"] is not None and
            (not isinstance(operation["source_oid"], str) or not OID.fullmatch(operation["source_oid"]))):
        errors.append("invalid native operation identity")
    for field, pattern in (("protected_paths", SHA256), ("protected_refs", OID)):
        values = record.get(field)
        if not isinstance(values, dict):
            errors.append(f"{field} must be a map")
            continue
        for target, value in values.items():
            if (field == "protected_paths" and not absolute(target)) or (field == "protected_refs" and not target.startswith("refs/")):
                errors.append(f"invalid {field} target")
            if not isinstance(value, str) or not pattern.fullmatch(value):
                errors.append(f"invalid {field} digest/OID")
    effects = record.get("verified_effects")
    if not isinstance(effects, list) or any(not isinstance(item, dict) or set(item) != {"kind", "target", "value"} or
            any(not isinstance(item[key], str) or not item[key] for key in ("kind", "target")) or
            not isinstance(item["value"], (str, dict)) or not item["value"] for item in effects):
        errors.append("verified_effects needs kind/target/value records of observed results")
    unknown = record.get("unknown_effects")
    if not isinstance(unknown, list) or any(not isinstance(value, str) or not value for value in unknown):
        errors.append("unknown_effects must be a list of unresolved effects")
    elif record.get("phase") == "verified" and unknown:
        errors.append("unknown effects cannot be reported as verified")
    elif record.get("phase") == "unknown" and not unknown:
        errors.append("unknown phase must identify an unresolved effect")
    if not isinstance(record.get("next_action"), str) or not record["next_action"].strip():
        errors.append("next_action must state the bounded next step or completed/no-op result")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    try:
        catalog = json.loads((Path(__file__).resolve().parents[1] / "skills/catalog.json").read_text(encoding="utf-8"))
        payload = json.loads(args.checkpoint.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else [payload]
        errors = [f"record {index}: {error}" for index, record in enumerate(records)
                  for error in checkpoint_errors(record, {row["name"] for row in catalog["skills"]})]
        if not records:
            errors.append("checkpoint journal must not be empty")
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}))
    raise SystemExit(2 if errors else 0)
