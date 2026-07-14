# Git Agent Skills

Evidence-driven Git workflow skills for AI coding agents. Skills are organized by **desired
postcondition**, not individual Git commands.

## Install

```sh
npx skills add hypercube-xyz/git-agent-skills
```

Install one skill when the installer supports selection:

```sh
npx skills add hypercube-xyz/git-agent-skills --skill craft-commits
```

## Design goals

- Route from user symptoms and outcomes, including non-technical phrasing.
- Inspect current state before selecting a command.
- Preserve unrelated work and prevent silent semantic escalation.
- Apply controls per reachable path: read-only, local mutation, shared/external, and critical impact.
- Keep `SKILL.md` focused; load conditional detail from direct references.
- Verify intended effects, incidental bounds, protected state, and remote results where applicable.

## Skill groups

Groups organize documentation and evaluation priority. Installers expose all skills unless they
support explicit selection.

### Core

| Skill | Scope |
|---|---|
| [`diagnose-repository`](skills/diagnose-repository/SKILL.md) | Build a precise, non-mutating explanation of the repository's current state and route the user to the smallest next workflow. |
| [`configure-git`](skills/configure-git/SKILL.md) | Establish the requested Git behavior at the narrowest valid scope while preserving unrelated configuration and revealing provenance. |
| [`craft-commits`](skills/craft-commits/SKILL.md) | Turn selected local work into the smallest complete, reviewable sequence of commits while preserving unrelated edits and the repository's message convention. |
| [`sync-branches`](skills/sync-branches/SKILL.md) | Make one local/remote branch relationship reach an explicitly chosen state without losing commits or silently choosing a divergence policy. |
| [`integrate-branches`](skills/integrate-branches/SKILL.md) | Create the intended integrated history at an exact local target while preserving contracts, unrelated work, and recoverability. |
| [`manage-worktrees`](skills/manage-worktrees/SKILL.md) | Establish the requested linked-worktree topology while protecting every registered worktree, checked-out branch, and uncommitted file. |
| [`resolve-conflicts`](skills/resolve-conflicts/SKILL.md) | Produce a semantically correct resolved tree, preserve intended behavior from all relevant sides, and complete or safely leave the operation in an explicit state. |
| [`undo-changes`](skills/undo-changes/SKILL.md) | Reach a specified earlier or inverse state while preserving all material work outside the exact reversal scope. |
| [`recover-lost-work`](skills/recover-lost-work/SKILL.md) | Identify the correct recoverable object with evidence, restore it under a new safe name or path, and avoid destroying remaining recovery evidence. |
| [`edit-commit-history`](skills/edit-commit-history/SKILL.md) | Produce the explicitly designed replacement commit series while preserving content, recovery anchors, signatures/policy, and concurrent remote work. |
| [`find-regression`](skills/find-regression/SKILL.md) | Identify a minimal causal boundary with a trustworthy test oracle and leave the repository in a known state. |
| [`manage-submodules`](skills/manage-submodules/SKILL.md) | Make the superproject's gitlink, `.gitmodules`, local submodule config, nested checkout, and expected remote relationship consistent. |
| [`manage-large-files`](skills/manage-large-files/SKILL.md) | Make selected large-file paths use the intended storage policy and remain retrievable without losing binary content or silently rewriting unrelated history. |
| [`manage-tags`](skills/manage-tags/SKILL.md) | Establish the exact requested tag object/ref locally or at a verified remote with correct type, target, annotation, signature, and immutability policy. |
| [`migrate-repository`](skills/migrate-repository/SKILL.md) | Transfer the explicitly selected repository state to a verified destination with auditable completeness, no credential leakage, and a controlled cutover/recovery plan. |

### Optional

| Skill | Scope |
|---|---|
| [`setup-repository`](skills/setup-repository/SKILL.md) | Produce one usable local repository at a verified destination without overwriting unrelated files or silently weakening repository completeness. |
| [`manage-remotes`](skills/manage-remotes/SKILL.md) | Make remote topology accurately represent the intended repositories and ref mappings without silently publishing or leaking authentication material. |
| [`manage-branches`](skills/manage-branches/SKILL.md) | Establish the intended local branch/ref state while preserving commits, worktree changes, linked worktrees, and remote refs. |
| [`preserve-work`](skills/preserve-work/SKILL.md) | Create a verified, recoverable snapshot of exactly the intended in-progress state while leaving excluded work protected. |
| [`transplant-commits`](skills/transplant-commits/SKILL.md) | Replay exactly the intended logical changes onto the target in a verified order without importing unrelated branch history. |
| [`investigate-history`](skills/investigate-history/SKILL.md) | Produce an evidence-backed history explanation with exact commits, paths, ranges, and limitations. |
| [`optimize-large-repository`](skills/optimize-large-repository/SKILL.md) | Reduce measured Git latency or transfer/storage cost while preserving correctness, required files/history, and recoverability. |

### Out-of-package boundaries

General code review, secret detection, and release preparation are not packaged as Git skills. Route
them to a dedicated SWE review workflow, an approved deterministic secret scanner, or the
repository's release procedure. `manage-tags` owns only the exact Git tag lifecycle.

See [`docs/SKILL-CATALOG.md`](docs/SKILL-CATALOG.md) for routing boundaries,
[`docs/HANDOFF-CONTRACT.md`](docs/HANDOFF-CONTRACT.md) for consequence-boundary handoffs, and
[`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) for supported environments.

## Development

```sh
python3 scripts/validate_skills.py
python3 scripts/evaluate_fixtures.py
python3 scripts/smoke_test_git.py
python3 scripts/build_release.py --check
```

List or link skills for local development:

```sh
./scripts/list-skills.sh
./scripts/link-skills.sh --dry-run
./scripts/link-skills.sh
```

Agent-runtime test cases are documented in
[`docs/VALIDATION-PLAN.md`](docs/VALIDATION-PLAN.md).

## License

MIT
