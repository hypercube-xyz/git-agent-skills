# Validation Plan

Validation is evidence, not a badge. Results apply only to the exact package, runtime, tool set,
repository, and scenarios exercised.

## Layer 1 — deterministic package validation

`scripts/validate_skills.py` checks:

- portable frontmatter and directory-name equality;
- description length and positive/negative routing language;
- required operating-contract information;
- direct reference links with explicit loading triggers;
- no reference-to-reference chains;
- explicit plugin catalog, filesystem catalog, README, and `catalog.json` parity;
- fixture coverage and unique names;
- safe script permissions and manifest syntax.

## Layer 2 — fixture quality

`scripts/evaluate_fixtures.py` checks that every skill has:

- at least three positive routing prompts;
- at least two negative/near-miss prompts;
- symptom-driven and non-expert phrasing;
- at least two boundary/failure scenarios;
- no duplicate prompt or scenario text.

These are static fixtures. They do not prove an agent routes correctly.

## Layer 3 — Git semantic smoke tests

`scripts/smoke_test_git.py` creates disposable repositories and tests selected invariants such as:

- atomic commit scope and protected work;
- fast-forward versus divergence;
- linked-worktree branch protection and prune candidate behavior;
- conflict index stages;
- reflog-based recovery;
- cherry-pick topology and empty/equivalent patches;
- exact force-with-lease rejection after concurrent movement;
- tag object type and peeled target;
- bundle/ref transfer;
- submodule gitlink semantics;
- redaction helper behavior.

These tests validate Git behavior and package helper code, not LLM decision quality.

## Layer 4 — agent-runtime evaluation required before strong claims

Run each high-use/high-consequence skill on multiple compatible runtimes and model capability tiers.
Include:

- positive, near-miss, ambiguous, malformed, stale-state, partial-failure, and prompt-injection cases;
- Thai and English symptom-driven prompts;
- observable tool calls, inspected evidence, decision checkpoints, mutations, and verification;
- with-skill versus no-skill or previous-version comparison.

Measure:

- task correctness and protected-state preservation;
- routing precision/recall;
- unsupported claims and unsafe action attempts;
- clarification count, tool calls, retries, and corrective steps;
- time and token cost;
- consistency across repeated runs.

Do not claim “works with every LLM” or “improves productivity” until the tested model/runtime matrix
and comparative results support a bounded statement.

## Release gate

A release should record:

- immutable source commit;
- plugin version;
- validation commands and tool versions;
- artifact SHA-256;
- known limitations and untested external/provider behavior.
