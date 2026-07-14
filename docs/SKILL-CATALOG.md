# Skill Catalog and Routing Boundaries

The package contains 22 skills. Groups organize documentation and evaluation priority; clients may
implement explicit skill selection.

## Core

`diagnose-repository`, `configure-git`, `craft-commits`, `sync-branches`, `integrate-branches`, `manage-worktrees`, `resolve-conflicts`, `undo-changes`, `recover-lost-work`, `edit-commit-history`, `find-regression`, `manage-submodules`, `manage-large-files`, `manage-tags`, `migrate-repository`

These workflows cover non-obvious Git state, topology, recovery, or consequential mutation. Evaluate
them first against supported runtimes.

## Compact / optional

`setup-repository`, `manage-remotes`, `manage-branches`, `preserve-work`, `transplant-commits`, `investigate-history`, `optimize-large-repository`

These workflows are lower-frequency or largely familiar to capable coding models. Keep their core
contracts compact and load references only for stated edge cases.

## Out-of-package boundaries

- Product or application code review: use a dedicated SWE review workflow. Git skills may establish
  an exact range but do not own review judgment.
- Repository secret scanning: use an approved deterministic scanner and a security triage workflow.
- Release preparation: use the repository's release procedure. `manage-tags` owns only the exact tag
  object/ref lifecycle.

## Frequent routing distinctions

- remote identity/refspec -> `manage-remotes`; branch relationship/push -> `sync-branches`
- local line integration -> `integrate-branches`; selected commits -> `transplant-commits`
- preserve existing work -> `preserve-work`; recover missing work -> `recover-lost-work`
- reverse a known state -> `undo-changes`; redesign an existing series -> `edit-commit-history`
- history explanation -> `investigate-history`; executable good/bad search -> `find-regression`
- LFS/storage policy -> `manage-large-files`; measured repository performance -> `optimize-large-repository`
- exact tag lifecycle -> `manage-tags`; versioning/build/artifact orchestration -> repository-specific workflow
- one-remote topology -> `manage-remotes`; whole-repository transfer/cutover -> `migrate-repository`

Use the compact handoff in [`HANDOFF-CONTRACT.md`](HANDOFF-CONTRACT.md) when crossing a material
consequence boundary or transferring mutable evidence.
