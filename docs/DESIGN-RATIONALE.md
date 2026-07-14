# Design Rationale

## Package objective

This package provides reusable Git workflow skills for AI coding agents. Each skill defines a
bounded operating procedure for one recurring outcome rather than acting as a command reference.

The common execution shape is:

```text
recognize the requested outcome
→ inspect current Git state
→ establish the exact target and protected state
→ choose the smallest complete operation
→ execute within the established boundary
→ verify the resulting state
→ report evidence and remaining uncertainty
```

## Routing by desired postcondition

Users usually describe an outcome or symptom, not the Git command required to solve it. Skills are
therefore routed by the state that should be true when the task is complete.

Examples:

- `sync-branches` owns the relationship between a local branch and a remote branch.
- `integrate-branches` owns combining complete lines of development locally.
- `transplant-commits` owns replaying selected commits without importing the source branch.
- `preserve-work` owns creating a recoverable snapshot before work is lost.
- `recover-lost-work` owns finding and restoring work after it is no longer normally reachable.
- `undo-changes` owns reaching a known earlier or inverse state.
- `edit-commit-history` owns designing and publishing a replacement commit series.

This separation avoids routing by isolated verbs such as “reset,” “pull,” or “rebase,” whose correct
meaning depends on the repository state and intended result.

## Skill boundaries

A skill is kept when it represents a coherent recurring outcome with distinct evidence, decision,
mutation, or verification requirements.

A skill is not created merely because Git exposes a separate command. Closely related commands stay
inside one skill when users cannot reasonably choose between them before inspection. For example,
`undo-changes` selects among restore, unstage, revert, reset, abort, and clean according to the
desired postcondition and recoverability requirements.

Adjacent skills remain separate when they have materially different completion criteria or risk
models. The principal distinctions are documented in
[`SKILL-CATALOG.md`](SKILL-CATALOG.md).

## Core and optional groups

The catalog uses two editorial groups:

- **Core** skills cover non-obvious Git state, recovery, topology, or consequential mutation.
- **Compact / optional** skills cover lower-frequency work or operations capable coding models
  usually handle correctly without extensive instruction.

These groups guide documentation and evaluation priority. They do not change runtime loading unless
an installer or client implements explicit skill selection.

## Out-of-package boundaries

The package excludes workflows whose primary ownership is not Git:

- Product and application code review belongs to a dedicated SWE review workflow.
- Secret detection belongs to an approved deterministic scanner and security triage workflow.
- Release preparation belongs to the repository's own versioning, build, artifact, and publication
  procedure.

Git skills may support these workflows by resolving exact refs, ranges, tags, or repository state,
but they do not own the broader decision.

This keeps routing precise and avoids generic skills that add context without supplying
Git-specific behavior.

## Evidence and state model

Git operations are selected from inspected state rather than command familiarity or model memory.

Skills distinguish the relevant layers explicitly:

- refs and object IDs;
- index state;
- working-tree state;
- untracked and ignored paths;
- operation metadata;
- worktree and submodule administration;
- local configuration and its provenance;
- remote observations and verified remote state.

Exact refs and object IDs are preferred when identity matters. Remote-tracking refs are treated as
local observations, not live remote truth.

## Mutation discipline

Mutation paths define:

- the desired postcondition;
- the exact target or bounded target set;
- protected state;
- expected incidental effects;
- prohibited effects;
- stop and replanning conditions.

Controls are proportional to the reachable effect:

- Read-only inspection emphasizes evidence and bounded claims.
- Local reversible mutation emphasizes preservation and final-state review.
- Shared or remote mutation verifies destination, freshness, and externally observable results.
- Destructive or history-rewriting operations require recovery anchors and stronger stale-state
  protection.

Low-risk paths are not burdened with checkpoints intended for destructive or external operations.

## Git-specific safety choices

The package favors Git mechanisms that preserve evidence and detect stale state:

- inspect before mutation;
- use exact refs, ranges, and object IDs where practical;
- separate fetch from integration;
- reject broad force pushes;
- bind rewritten branch and tag updates to exact observed remote object IDs;
- create recovery anchors before destructive history changes;
- preview prune and clean candidate sets;
- preserve unrelated worktrees, submodules, refs, and untracked content;
- verify remote refs after publication;
- treat command success as evidence only for what that command establishes.

Broad cleanup, wildcard ref updates, and repository-wide rewriting are avoided when a narrower
operation satisfies the requested outcome.

## Context architecture

Each `SKILL.md` contains the instructions required on most activations:

- objective and routing boundaries;
- required evidence;
- non-obvious invariants;
- decision and action boundaries;
- workflow;
- stop conditions;
- verification and output expectations.

Conditional detail is placed in a directly linked reference and loaded only under a stated trigger.
Deterministic scripts are used for mechanical inspection or validation when code is safer and more
consistent than regenerated shell logic.

Reference chains and duplicated general doctrine are avoided.

## Cross-skill handoff

Normal tasks may require more than one skill. A handoff is used only when mutable evidence or a
material consequence boundary must be carried forward.

The compact handoff records the established state, exact object IDs, protected state, unresolved
unknowns, partial effects, and recovery anchors. Mutable state is re-inspected near the next action
boundary, and a broader action does not inherit authority or confirmation from a narrower action by
default.

See [`HANDOFF-CONTRACT.md`](HANDOFF-CONTRACT.md).

## Validation strategy

Validation is layered:

1. Structural validation checks frontmatter, package layout, direct references, and catalog parity.
2. Routing fixtures cover positive triggers, near misses, and out-of-package boundaries.
3. Scenario fixtures cover ambiguity, protected state, partial failure, and consequential paths.
4. Git smoke tests verify mechanical behavior and previously observed regressions.
5. Agent-runtime cases are reserved for routing, tool-use, and decision behavior that static tests
   cannot establish.

Validation effort is concentrated on high-risk and high-confusion workflows rather than applied
uniformly to every skill.

See [`VALIDATION-PLAN.md`](VALIDATION-PLAN.md).

## Criteria for changing the catalog

Add a skill when all of the following are true:

- the outcome recurs across repositories;
- it has a coherent activation boundary;
- it requires non-obvious Git-specific decisions or safeguards;
- it can define observable completion criteria;
- a separate skill improves behavior more than it increases routing and context cost.

Reduce, merge, or remove a skill when evaluation shows that it duplicates normal model capability,
routes ambiguously, or adds context without improving correctness, safety, or verification.
