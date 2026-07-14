# Validation Plan

Validation uses five layers.

## 1. Package contract

`python3 scripts/validate_skills.py` checks catalog parity, frontmatter, direct references, required
runtime-contract elements, context-size heuristics, package files, group completeness, and selected
high-consequence invariants.

## 2. Static routing and failure fixtures

`python3 scripts/evaluate_fixtures.py` checks every case in `tests/routing.json` and at least two
boundary/failure scenarios per skill. Each routing case records:

- expected and forbidden skills;
- expected consequence classes;
- evidence that should be inspected;
- actions that must not occur.

These fixtures check coverage and reviewability. Model execution is covered by layer 4.

## 3. Deterministic Git and package semantics

`python3 scripts/smoke_test_git.py` uses disposable repositories to test selected invariants,
including exact force-with-lease rejection, post-push remote queries, tag objects, NUL-safe worktree
and filename handling, destructive-clean preview, linked-worktree protection, reflog recovery,
shared-tag-namespace prune visibility, atomic multi-ref push, submodule gitlinks, remote redaction,
and installer preflight behavior.

## 4. Agent-runtime evaluation

`tests/agent-runtime-cases.json` contains observable cases that static validation does not run. Run
high-risk skills and overlapping routing pairs against each supported runtime and model tier.
Capture tool calls, inspected sources, checkpoints, mutations, retries, validation, and final
results.

Measure task success, protected-state violations, unsafe attempts, routing confusion, tool calls,
clarification count, token cost, and repeated-run consistency. Use `without skill`, `current skill`,
and `reduced skill` comparisons for skills whose marginal value is uncertain.

## 5. Release gate

`python3 scripts/build_release.py --check` runs the static and semantic checks, builds two independent
archives, compares them byte-for-byte, and emits:

- a versioned ZIP;
- a SHA-256 sidecar;
- a release JSON containing source-tree identity, tool versions, validation status, artifact hash,
  and tested environment.
