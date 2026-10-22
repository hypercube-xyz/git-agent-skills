"""Read-only Git preflight; reports observations, never certifies a sandbox or authorizes work.

This process has a timeout and disables optional index writes and fsmonitor for its
own commands. Those controls do not apply automatically to an agent's later commands.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from security_git_env import resolve_git


def probe(repository: Path, *, git_executable=None):
    # Preserve effective config for inspection, but do not accept ambient repo selectors.
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG"):
        env.pop(key, None)
    env.update(GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", GIT_PAGER="cat")
    executable = resolve_git(git_executable)

    def read(*args):
        return subprocess.run([executable, "--no-optional-locks", "-c", "core.fsmonitor=false", *args],
                              cwd=repository, env=env, capture_output=True, timeout=10, check=True).stdout

    git_dir = read("rev-parse", "--absolute-git-dir").decode("utf-8").rstrip("\n")
    # Config values may be secrets; retain category counts only, never output values or URL keys.
    names = read("config", "--null", "--list", "--name-only").decode("utf-8").split("\0")
    surfaces = {"hooks": 0, "filters": 0, "helpers": 0, "rewrites": 0, "drivers": 0, "fsmonitor": 0}
    for name in names:
        key = name.lower()
        if key == "core.hookspath": surfaces["hooks"] += 1
        if key.startswith("filter."): surfaces["filters"] += 1
        if key.startswith("credential.") or key in {"core.sshcommand", "core.gitproxy"}: surfaces["helpers"] += 1
        if key.startswith("url."): surfaces["rewrites"] += 1
        if key.startswith(("diff.", "merge.")): surfaces["drivers"] += 1
        if key == "core.fsmonitor": surfaces["fsmonitor"] += 1
    return {"schema_version": 1, "git_dir": git_dir,
            "observed": {"git_available": True, "repository_identity": True},
            "enforced_for_probe_only": ["subprocess_timeout", "fsmonitor_disabled", "optional_index_writes_disabled"],
            "execution_surface_counts": surfaces,
            "not_proven": ["filesystem_isolation", "network_isolation", "credential_isolation", "approval_enforcement"],
            "authorization": "none; inspect the actual runtime and destination before the affected action"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--require", action="append", default=[],
                        choices=("filesystem_isolation", "network_isolation", "credential_isolation", "approval_enforcement"),
                        help="Fail closed when a plan needs a control this probe cannot prove")
    args = parser.parse_args()
    try:
        report = probe(args.repository)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        # stderr/config output can contain secrets; report only the failure class.
        print(json.dumps({"probe_completed": False, "error_type": type(exc).__name__}))
        return 2
    report["unmet_requirements"] = args.require
    print(json.dumps(report))
    return 2 if args.require else 0


if __name__ == "__main__":
    raise SystemExit(main())
