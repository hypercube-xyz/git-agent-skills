# Git Agent Skills v2 plan

## Outcome and baseline

All 24 independently installable skills will guide evidence-based Git decisions,
execution, recovery, and verification. The target is competent engineering behavior,
not command memorization or a claim that instructions guarantee model correctness.

Authoring baseline: Agent Skills Engineering Standard 0.1.1, supplied locally by
the maintainer; apply its Engineering Baseline and Software Engineering profile,
plus operational controls for publication/cutover. Runtime-critical rules must be
in the installed skill, without depending on that private baseline.

Starting revision: `1c1054041f988fb7a5ce863d9829d4946fdd1f57`. The 24 staged skill
edits present at task start are input, not disposable work. Preserve their useful
corrections. Leave unrelated `.serena/` content alone.

## Design decisions

- Retain the 24 outcome-based names: discovery has not established that merging
  owners improves routing. Breaking change is the operating contract, not renaming
  for its own sake. Keep independent single-skill installation working.
- Replace repetitive generic ceremony with concise standalone controls. Retain
  exact targets, protected state, executable Git boundaries, sensitive output,
  freshness, recovery, partial outcomes, and verifiable completion where relevant.
- Every skill must connect observed evidence to a Git-specific choice and its
  verification. Explain traps that change that choice. Provide useful commands as
  examples with conditions, not an unconditional shell recipe.
- Conditional playbooks must add mechanics and decision branches, not repeat the
  entrypoint. Keep direct loading triggers; avoid a mandatory umbrella skill,
  shared-file dependency outside the installed folder, or content generator.
- A skill handoff preserves existing authorization and completed work. Support
  inspection, preview, and execution without invented approval loops. Ambiguity
  blocks only the action that depends on it.
- Feature-detect optional Git behavior. Never assume `.git` is a directory,
  every object ID has 40 characters, remote-tracking refs are live truth, or a
  clean status proves ignored files/unique detached commits are expendable.
- Preserve hooks, signing, filters, and repository policy needed for the intended
  result. Disable unnecessary untrusted execution without presenting a config
  override as an operating-system sandbox or bypassing required policy.

## Work sequence and ownership

1. Sol discovery: read all skills/resources and inspect packaging/evaluation gaps.
2. Root: freeze this design, define acceptance criteria, retain final review ownership.
3. Sol high: rewrite all skills and conditional references; update consistent
   package metadata and documentation for 2.0.0. Add focused mechanical regression
   checks for changed examples or confirmed gaps. Do not publish or commit.
4. Root: review every resulting skill/reference and full diff against source
   evidence; send concrete findings back to Sol high until addressed.
5. Independent blind execution: give agents realistic tasks and raw disposable
   repositories without expected answers; inspect tool traces and resulting state.
   Cover routine work, material ambiguity, protected state, recovery, conflicts,
   concurrency/publication, and untrusted content. Repeat failed cases after fixes.
6. Release: run required checks, commit reviewed content, publish through the
   repository's verified workflow, and verify exact tag/source/artifact identity.
   An unavailable release prerequisite remains an explicit blocker.

## Skill-specific acceptance surfaces

| Skills | Required decision know-how |
|---|---|
| diagnose, investigate, regression | HEAD/index/worktree distinctions; operation discovery via Git paths; history completeness; search semantics; classifier exits and inconclusive boundaries |
| configure, setup, remotes | effective scope/provenance; empty/bare/filtered clones; configured versus effective endpoints; rewrite rules and credential-safe inspection |
| commits, preserve, undo, recover | selected staged tree; partial staging; hooks; stash classes and restoration; exact reversal state; typed additive recovery and limits |
| integrate, conflicts, transplant | ancestry versus patch equivalence; merge/rebase choices; base/stage semantics; continue ownership; dependencies, mainline, empty and mailbox outcomes |
| history, stacks | old boundaries and retained recovery refs; updateRefs; per-layer diff; landed squash changes; signatures; expected-old ref updates and exact leases |
| branches, worktrees | explicit start and tracking; occupancy; ignored collisions; detached retention; prune candidate set and mount/path identity |
| submodules, large files | gitlink versus nested work; URL resolution; pinned versus remote update; payload versus pointer; attributes and selected staged snapshot |
| repair, optimize, migration, tags | damage versus omission; verified recovery source; measured bottleneck; transfer manifest; exact tag object versus peeled target; endpoint read-back and partial outcomes |

## Verification and release acceptance

- All 24 skills and their references receive direct substantive review. No
  unresolved finding that can lose work, misroute consequential action, fabricate
  evidence, or cross an authorization boundary.
- Structural/routing inventories pass; static phrases and recorded old routing
  scores are never described as new agent execution evidence.
- Git semantic and security checks pass on the exercised environment; cross-OS
  claims require the existing CI matrix. Fix the platform selector if confirmed
  to omit portable cases from platform runs.
- Preserve old evaluation records as historical evidence. New evaluation results
  identify exact inputs, model/runtime, actions, assertions, failures, and limits.
- Correct stale release documentation. Release input remains immutable committed
  blobs; checks execute separately. Do not weaken release or validation gates.
- Publish 2.0.0 only after release prerequisites pass. Verify remote tag identity,
  workflow result, and downloadable artifact checksums before calling it released.

## Compatibility

Version 2 changes instruction structure and procedural expectations across every
skill. Consumers parsing prose/headings must migrate; names and installation
paths remain stable. Keep runtime helpers compatible unless a demonstrated defect
requires a documented schema change. No automatic rewrite of consumer repositories
or installed personal skills is part of this release.
