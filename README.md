# Git Agent Skills

Evidence-driven Git workflow skills for AI coding agents. Skills are organized by **desired postcondition**, not individual Git commands.

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
python3 scripts/smoke_test_git.py
python3 scripts/build_release.py --check
```

Link all packaged skills for local development:

```sh
python3 scripts/link_skills.py --dry-run
python3 scripts/link_skills.py
```

The release builder is a pure packager: it reads immutable committed blobs via `git ls-tree` and `git cat-file`, never touches the working tree, and does not run validators. CI validates the checked-out revision before calling the builder. Each release output (ZIP, checksum, metadata) is written atomically per file; abrupt termination may leave a partial output set — rerunning the deterministic builder reconciles it.

## Compatibility

- **Skills and installation:** Linux, macOS, Windows (Python 3.14, Git 2.35+)
- **Release publishing:** Linux CI only; artifact is a platform-neutral ZIP
- **No OS/process sandbox** is provided by this repository
- **Concurrent local attacker** with write access to the output parent directory is not defended against (known TOCTOU limitation)
- **Hard-killed processes** may leave temporary directories in the OS temp prefix

## License

MIT
