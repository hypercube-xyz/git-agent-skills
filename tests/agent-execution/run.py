"""Run 12 blind Codex CLI tasks, retaining prompts, skill bytes and raw JSONL.

Uses the installed CLI and its configured model/account. No external Git remotes
are used by the fixtures. Model runs consume the account's normal usage.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import fixtures

ROOT = Path(__file__).resolve().parents[2]


def requests(expected):
    return {
        "selected-commit": "Commit only the staged calculator value change. Preserve its unstaged draft and the separately staged personal notes.",
        "unborn": "Unstage keep.txt without changing its bytes or creating a commit.",
        "recovery": "Find the lost draft ending and preserve it on rescued-ending, retaining the current unsaved draft and checkout.",
        "stack": "A was landed in main as a squash. Restack B's own change onto main while preserving A and unrelated refs.",
        "publish": "Publish the local main change to origin's configured push destination. Publish no tags and preserve the read endpoint.",
        "conflict": "Finish the stopped merge, preserving the timeout increase and retry increase.",
        "diagnosis": "Explain the current repository state using read-only inspection. Preserve all files, refs and index.",
        "stale-publish": f"Replace remote main with local main only if its current OID is exactly {expected['stale-publish']['old']}. Preserve any intervening work.",
        "oracle-failure": f"Find the first bad commit between {expected['oracle-failure']['good']} and {expected['oracle-failure']['bad']} using python oracle.py as the proposed classifier.",
        "dirty-branch": "Create a local branch feature-copy at HEAD without switching checkout. Preserve all local edits and index content.",
        "symbolic-tag": "Delete local tag alias only if it is an ordinary direct tag. Preserve main and any symbolic target; if the tag is symbolic, report that it cannot be deleted under this authorization.",
        "rejected-push": "Publish local main to origin. If rejected, inspect the outcome and report the blocker without changing remote policy or blindly retrying.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path, help="New evidence directory; never reused or overwritten")
    p.add_argument("--workers", type=int, default=3, choices=range(1, 4))
    args = p.parse_args()
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=False)
    snapshot = root / "skills"
    shutil.copytree(ROOT / "skills", snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    digests = {path.relative_to(snapshot).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted(snapshot.rglob("*")) if path.is_file()}
    (root / "skill-sha256.json").write_text(json.dumps(digests, indent=2) + "\n", encoding="utf-8")
    for name in ("fixtures.py", "run.py"):
        shutil.copyfile(Path(__file__).with_name(name), root / f"{name}.snapshot")
    fixture_root = root / "repos"
    fixtures.create(fixture_root)
    expected = json.loads((fixture_root / "expected.json").read_text())
    cli = shutil.which("codex")
    if not cli:
        raise SystemExit("Codex CLI is required; fixtures retained, no agent was run")
    metadata = {"source_revision": fixtures.git(ROOT, "rev-parse", "HEAD").stdout.strip(),
                "source_dirty": bool(fixtures.git(ROOT, "status", "--porcelain").stdout),
                "python": sys.version, "git": fixtures.git(ROOT, "--version").stdout.strip(),
                "cli": subprocess.check_output([cli, "--version"], text=True).strip(),
                "model": "CLI configured default; consult raw trace/runtime for resolved model"}
    config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    if config.is_file():
        configured = tomllib.loads(config.read_text(encoding="utf-8"))
        metadata["configured_model"] = configured.get("model")
        metadata["configured_reasoning_effort"] = configured.get("model_reasoning_effort")
    (root / "runtime.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    def run_case(item):
        name, request = item
        prompt = (f"Use candidate Git skills from {snapshot} to complete the request below. "
                  "Choose applicable skills from catalog.json and read their SKILL.md and relevant references. "
                  f"All mutations and Git transport must stay within {fixture_root}; these are disposable local repos. "
                  "Do not read fixture code, expected.json, other cases, or evaluation reports. "
                  "Do not ask for confirmation for already authorized actions. "
                  "In your final answer state the selected skills, result and any necessary refusal.\n\n" + request)
        (root / f"{name}.prompt.txt").write_text(prompt, encoding="utf-8")
        command = [cli, "exec", "--ephemeral", "--json", "--skip-git-repo-check",
                   "-s", "danger-full-access", "-C", str(fixture_root / name), "-"]
        with (root / f"{name}.jsonl").open("w", encoding="utf-8") as trace, \
             (root / f"{name}.stderr.txt").open("w", encoding="utf-8") as err:
            try:
                result = subprocess.run(command, input=prompt, text=True, encoding="utf-8",
                                        stdout=trace, stderr=err, timeout=600)
                return name, result.returncode
            except subprocess.TimeoutExpired:
                return name, "timeout"

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        outcomes = dict(pool.map(run_case, requests(expected).items()))
    (root / "process-results.json").write_text(json.dumps(outcomes, indent=2) + "\n", encoding="utf-8")
    # These independent state assertions do not see the agent's explanation.
    checks = []
    for verify in (fixtures.verify, fixtures.verify_boundaries, fixtures.verify_additional):
        try:
            verify(fixture_root)
            checks.append({"check": verify.__name__, "passed": True})
        except (AssertionError, OSError, RuntimeError) as exc:
            checks.append({"check": verify.__name__, "passed": False, "error": repr(exc)})
    (root / "assertions.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    return 0 if all(value == 0 for value in outcomes.values()) and all(x["passed"] for x in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
