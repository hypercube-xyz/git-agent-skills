# Validation Report

Date: 2026-07-15  
Package: `git-agent-skills`  
Plugin version: `1.0.0`

## Results

```text
PASS: 22 skill packages and catalog groups
PASS: 111 routing fixtures
PASS: 52 boundary/failure scenarios
PASS: 25 local Git/package semantic smoke tests
PASS: deterministic release archive generation with exactly one embedded manifest
```

Commands:

```sh
python3 scripts/validate_skills.py
python3 scripts/evaluate_fixtures.py
python3 scripts/smoke_test_git.py
python3 scripts/build_release.py --check
```

The semantic suite covers exact branch/tag lease rejection after concurrent movement, ordinary
post-push remote verification, tag object/peeling semantics, NUL-safe worktree and pathological
filename handling, destructive-clean preview, both non-obstructing and obstructing hard-reset cases,
conflict stages and abort, shared-tag-namespace prune candidates, reflog recovery, atomic multi-ref
push, submodule gitlinks, corrected history pickaxe/bisect behavior, remote names containing dots or
slashes, fail-closed remote redaction, skipped-validation manifest metadata, and installer
preflight/rollback behavior.

## Agent-runtime cases

`tests/agent-runtime-cases.json` defines cases for untrusted routing keywords, stale remote state,
exact lease behavior, pathological filenames, and migration phase separation. These cases were not
run in this report.

## Tests not run

- model routing and tool-use evaluation;
- with-skill versus no-skill comparison;
- provider authentication, branch protection, hosted release, and migration policy behavior;
- macOS and Windows execution.

Release artifacts record the source-tree digest, archive hash, tool versions, validation results,
and tested environment.
