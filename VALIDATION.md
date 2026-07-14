# Validation Report

Date: 2026-07-15

Package: `git-agent-skills`

Plugin version: `1.0.0`

This report distinguishes package checks, Git semantic tests, installer/plugin compatibility checks,
and evaluation that has **not** been performed.

## Performed

### Package and routing structure

```text
PASS: 25 skills
PASS: plugin, filesystem, catalog.json, frontmatter, and README catalogs
PASS: 125 routing fixtures
PASS: 50 boundary/failure scenarios
PASS: positive/negative coverage, symptom phrasing, multilingual signal, and uniqueness
```

Command:

```sh
python3 scripts/validate_skills.py
python3 scripts/evaluate_fixtures.py
```

The routing fixtures are static cases. They establish coverage and test-data quality, not actual
model routing accuracy.

### Local Git semantic smoke tests

```text
PASS: 20 local Git semantic smoke tests
```

Covered invariants include:

- unborn branch and porcelain-v2 signals;
- configuration origin/scope;
- fail-closed remote credential redaction;
- selected atomic commit scope and protected untracked work;
- branch deletion ancestry and linked-worktree protection;
- fast-forward versus diverged remote synchronization;
- fast-forward integration;
- non-destructive patch preservation;
- complete worktree-prune candidate observation;
- conflict index stages and abort;
- unstage while preserving worktree content;
- reflog-based recovery to a new ref;
- cherry-pick parent/topology and already-applied empty result;
- exact force-with-lease rejection after concurrent remote movement;
- pickaxe history search;
- automated bisect boundary;
- annotated versus lightweight tag objects and peeling;
- sparse checkout preserving object content;
- submodule gitlink mode/OID;
- explicit-ref bundle transfer.

Command:

```sh
python3 scripts/smoke_test_git.py
```

These tests establish selected Git/tool semantics. They do not execute an LLM or prove the agent
will choose the correct skill, inspect enough evidence, or follow every boundary.

### Reproducible release archive

```text
PASS: two independently generated archives were byte-identical
```

Command:

```sh
python3 scripts/build_release.py --check
```

The final artifact SHA-256 is recorded in the generated `.sha256` sidecar.

### Installer and plugin compatibility

Tested with:

```text
Skills CLI: 1.5.17
Claude Code: 2.1.209
```

Commands:

```sh
CI=1 npx --yes skills@1.5.17 add . --list
npx --yes @anthropic-ai/claude-code@2.1.209 plugin validate . --strict
```

Observed:

```text
PASS: Skills CLI discovered 25 skills
PASS: skills were grouped under Git Agent Skills
PASS: Claude Code plugin manifest strict validation
```

The GitHub shorthand installation cannot be tested until this exact package is pushed to the
target repository.

## Not performed

- real-agent routing evaluation;
- tool-call and observable execution review across model tiers;
- with-skill versus no-skill productivity comparison;
- GitHub/GitLab/Bitbucket authentication and policy behavior;
- live branch protection, signed commit/tag trust, LFS provider, package registry, or deployment;
- production migration/cutover or destructive recovery tests;
- guarantees for every LLM or agent runtime.

## Required before strong behavioral claims

Run the matrix in [`docs/VALIDATION-PLAN.md`](docs/VALIDATION-PLAN.md) and record immutable source
commit, model/runtime/tool versions, task fixtures, observable execution evidence, measurements,
failures, and bounded conclusions.
