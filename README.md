# Git Agent Skills

Git Agent Skills v2 gives coding agents evidence-based decisions for 24 Git outcomes. Each independently installable skill connects observed repository state to a bounded Git action and checks the resulting state.

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

See [`docs/SECURITY-EXECUTION.md`](docs/SECURITY-EXECUTION.md) for the common untrusted-content, executable-Git, retry, recovery-artifact, and runtime-enforcement contract.

Version 2 changes the skill instruction contract while keeping all 24 names and installation paths. Consumers that parse skill prose or headings should review the new layout. The bundled remote helper now reports configured and effective fetch/push endpoints; its output still needs review before display because host, path, remote name, and config origin can contain sensitive data.

## Skill groups

Groups organize documentation and evaluation priority. Installers expose all skills unless they support explicit selection.

### Core

| Skill | Scope |
|---|---|
| [`diagnose-repository`](skills/diagnose-repository/SKILL.md) | Classify confusing Git state without mutation and route to the owning workflow. |
| [`configure-git`](skills/configure-git/SKILL.md) | Own Git configuration, identity, signing, attributes, hooks, and helper selection. |
| [`craft-commits`](skills/craft-commits/SKILL.md) | Turn reviewed local changes into coherent atomic commits. |
| [`sync-branches`](skills/sync-branches/SKILL.md) | Reconcile and publish one local/remote branch relationship. |
| [`integrate-branches`](skills/integrate-branches/SKILL.md) | Integrate one complete line, including subtree/vendor synchronization. |
| [`manage-worktrees`](skills/manage-worktrees/SKILL.md) | Own linked-worktree lifecycle and branch occupancy safety. |
| [`resolve-conflicts`](skills/resolve-conflicts/SKILL.md) | Resolve semantic conflicts after a Git operation has stopped. |
| [`undo-changes`](skills/undo-changes/SKILL.md) | Reverse a known change or abort known operation state. |
| [`recover-lost-work`](skills/recover-lost-work/SKILL.md) | Restore intact but unreachable/deleted work additively. |
| [`repair-repository-integrity`](skills/repair-repository-integrity/SKILL.md) | Repair damaged/missing Git objects, packs, refs, alternates, or clone completeness. |
| [`edit-commit-history`](skills/edit-commit-history/SKILL.md) | Rewrite one existing commit series in place. |
| [`find-regression`](skills/find-regression/SKILL.md) | Locate a behavioral transition with a validated bisect oracle. |
| [`manage-submodules`](skills/manage-submodules/SKILL.md) | Own `.gitmodules`, gitlinks, and nested repository relationships. |
| [`manage-large-files`](skills/manage-large-files/SKILL.md) | Own LFS pointer/object relationships and large-object policy. |
| [`manage-tags`](skills/manage-tags/SKILL.md) | Own tag object/ref lifecycle and verification. |
| [`migrate-repository`](skills/migrate-repository/SKILL.md) | Transfer a complete repository and coordinated migration state. |

### Compact / optional

| Skill | Scope |
|---|---|
| [`setup-repository`](skills/setup-repository/SKILL.md) | Create or clone a repository with the intended topology and completeness policy. |
| [`manage-remotes`](skills/manage-remotes/SKILL.md) | Own remote identity, URLs, refspecs, and fork/upstream topology. |
| [`manage-branches`](skills/manage-branches/SKILL.md) | Own local branch lifecycle and metadata without integration. |
| [`preserve-work`](skills/preserve-work/SKILL.md) | Create a verified temporary rescue artifact from current uncommitted work. |
| [`transplant-commits`](skills/transplant-commits/SKILL.md) | Replay selected commits or reviewed patch/mailbox series. |
| [`investigate-history`](skills/investigate-history/SKILL.md) | Explain provenance and historical change without mutation. |
| [`optimize-large-repository`](skills/optimize-large-repository/SKILL.md) | Measure and tune a healthy large repository. |
| [`manage-stacked-branches`](skills/manage-stacked-branches/SKILL.md) | Restack and coordinate publication of dependent review branches. |

## Boundaries and references

General code review, secret detection, release preparation, hosting-provider administration, and deployment are outside this package. Multi-step Git know-how is kept in the direct references of the skill that owns the consequential decision, so installed agents can discover it without an umbrella workflow skill.

See [`docs/SKILL-CATALOG.md`](docs/SKILL-CATALOG.md) for routing boundaries, [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) for supported environments, and [`docs/DESIGN-RATIONALE.md`](docs/DESIGN-RATIONALE.md) for the package design. Consequence-boundary handoff fields are stated directly in the relevant skills so they remain available when a skill is installed independently.

## Development

```sh
python3 scripts/validate_skills.py
python3 scripts/security_regression.py
python3 scripts/review_regressions.py
python3 scripts/recheck_regressions.py
python3 -m unittest discover -s scripts -p 'test_release_version.py' -v
python3 -m unittest discover -s scripts -p 'test_file_safety.py' -v
python3 -m unittest discover -s scripts -p 'test_skill_contracts.py' -v
python3 scripts/smoke_test_git.py
python3 scripts/build_release.py --check
# Build packages committed source; run after committing reviewed changes.
# Release CI also requires --release-tag v<catalog-version>.
```

Link all packaged skills for local development:

```sh
python3 scripts/link_skills.py --dry-run
python3 scripts/link_skills.py
```

The bundled copy installer records SHA-256 file hashes and directory layout at install
time. An unchanged copy upgrades automatically. Added, edited or deleted files (including
empty directory changes) stop the entire preflight and leave all destinations untouched.
Legacy copies without a content manifest also stop because their original bytes are unknown.
Preserve or merge local edits first; `--force-copies` explicitly replaces directory contents
and discards local changes. It does not bypass link/reparse-point checks. Content is checked
again before each replacement, and earlier replacements roll back if that check fails.

Static fixtures and historical routing scores do not establish v2 agent behavior. See [`docs/VALIDATION-PLAN.md`](docs/VALIDATION-PLAN.md) for the required blind execution checks and release evidence.

Routing responsibility and execution decisions are separate. Conditional multi-intent
fixtures and the optional handoff/resume checkpoint format are described in
[`docs/HANDOFF-CONTRACT.md`](docs/HANDOFF-CONTRACT.md). Each skill carries the checkpoint
fields inline for standalone installation; the shared validator is an optional data
check and never grants authorization or executes Git actions.

v2.0.2 matches inspection to read-only, reversible-local, shared and destructive
effects. Routine local branch/tag creation needs no remote survey or handoff JSON.
Compact checkpoint v2 omits inapplicable fields; full v1 checkpoints remain accepted.
Conditional transport details ship inside each affected skill, preserving standalone
installation. The optional `python scripts/runtime_capabilities.py <repository>`
reports observable probe controls and unproven runtime isolation, not a security certificate.

Each skill starts from the requested outcome, investigates material concerns and
uses the smallest adequate procedure. Evidence lists apply to the selected mode;
they are not universal checklists. Existing authorization carries through handoffs,
and verification ends when the outcome and relevant protected-state checks are met.
See the [capability matrix](docs/COMPATIBILITY.md#feature-detection) for Git 2.35,
NUL worktree inventory and ref-backend limits.

The release builder is a pure packager: it reads immutable committed blobs via `git ls-tree` and `git cat-file`, does not read working-tree file content as package input, and does not run validators. CI validates the checked-out revision before calling the builder. Each release output (ZIP, checksum, metadata) is written atomically per file; abrupt termination may leave a partial output set — rerunning the deterministic builder reconciles it.

## Compatibility

- **Skills and installation:** Linux, macOS, Windows (Python 3.14, Git 2.35+)
- **Release publishing:** Linux CI only; artifact is a platform-neutral ZIP
- **No OS/process sandbox** is provided by this repository
- **Concurrent local attacker** with write access to the output parent directory is not defended against (known TOCTOU limitation)
- **Hard-killed processes** may leave process-local directories in the OS temp prefix and installer staging or backup directories beside the target

## License

MIT
