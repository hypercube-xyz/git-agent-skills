# Skill catalog

Skills are routed by desired postcondition. Tiers organize documentation and evaluation priority; they do not grant authority or change consequence controls.

| Skill | Tier | Central outcome |
|---|---|---|
| [`diagnose-repository`](../skills/diagnose-repository/SKILL.md) | Core | Classify confusing Git state without mutation and route to the owning workflow. |
| [`configure-git`](../skills/configure-git/SKILL.md) | Core | Own Git configuration, identity, signing, attributes, hooks, and helper selection. |
| [`craft-commits`](../skills/craft-commits/SKILL.md) | Core | Turn reviewed local changes into coherent atomic commits. |
| [`sync-branches`](../skills/sync-branches/SKILL.md) | Core | Reconcile and publish one local/remote branch relationship. |
| [`integrate-branches`](../skills/integrate-branches/SKILL.md) | Core | Integrate one complete line, including subtree/vendor synchronization. |
| [`manage-worktrees`](../skills/manage-worktrees/SKILL.md) | Core | Own linked-worktree lifecycle and branch occupancy safety. |
| [`resolve-conflicts`](../skills/resolve-conflicts/SKILL.md) | Core | Resolve semantic conflicts after a Git operation has stopped. |
| [`undo-changes`](../skills/undo-changes/SKILL.md) | Core | Reverse a known change or abort known operation state. |
| [`recover-lost-work`](../skills/recover-lost-work/SKILL.md) | Core | Restore intact but unreachable/deleted work additively. |
| [`repair-repository-integrity`](../skills/repair-repository-integrity/SKILL.md) | Core | Repair damaged/missing Git objects, packs, refs, alternates, or clone completeness. |
| [`edit-commit-history`](../skills/edit-commit-history/SKILL.md) | Core | Rewrite one existing commit series in place. |
| [`find-regression`](../skills/find-regression/SKILL.md) | Core | Locate a behavioral transition with a validated bisect oracle. |
| [`manage-submodules`](../skills/manage-submodules/SKILL.md) | Core | Own `.gitmodules`, gitlinks, and nested repository relationships. |
| [`manage-large-files`](../skills/manage-large-files/SKILL.md) | Core | Own LFS pointer/object relationships and large-object policy. |
| [`manage-tags`](../skills/manage-tags/SKILL.md) | Core | Own tag object/ref lifecycle and verification. |
| [`migrate-repository`](../skills/migrate-repository/SKILL.md) | Core | Transfer a complete repository and coordinated migration state. |
| [`setup-repository`](../skills/setup-repository/SKILL.md) | Compact / optional | Create or clone a repository with the intended topology and completeness policy. |
| [`manage-remotes`](../skills/manage-remotes/SKILL.md) | Compact / optional | Own remote identity, URLs, refspecs, and fork/upstream topology. |
| [`manage-branches`](../skills/manage-branches/SKILL.md) | Compact / optional | Own local branch lifecycle and metadata without integration. |
| [`preserve-work`](../skills/preserve-work/SKILL.md) | Compact / optional | Create a verified temporary rescue artifact from current uncommitted work. |
| [`transplant-commits`](../skills/transplant-commits/SKILL.md) | Compact / optional | Replay selected commits or reviewed patch/mailbox series. |
| [`investigate-history`](../skills/investigate-history/SKILL.md) | Compact / optional | Explain provenance and historical change without mutation. |
| [`optimize-large-repository`](../skills/optimize-large-repository/SKILL.md) | Compact / optional | Measure and tune a healthy large repository. |
| [`manage-stacked-branches`](../skills/manage-stacked-branches/SKILL.md) | Compact / optional | Restack and coordinate publication of dependent review branches. |

## High-risk routing intersections

- Intact but unreachable work: `recover-lost-work`; object/ref/pack corruption or broken clone completeness: `repair-repository-integrity`.
- One complete line of history: `integrate-branches`; selected commits/mailbox series: `transplant-commits`; dependent review-branch DAG: `manage-stacked-branches`.
- One local/remote branch relationship and publication: `sync-branches`; coordinated stack publication remains owned by `manage-stacked-branches`.
- Durable, reviewable project history: `craft-commits`; temporary WIP commits, stashes, safety branches, or rescue artifacts: `preserve-work`.
- Temporary rescue patch for local work: `preserve-work`; externally supplied reviewed patch/mailbox series: `transplant-commits`.
- Subtree/vendor content integrated into the superproject tree: `integrate-branches`; gitlinks and nested repositories: `manage-submodules`.
- LFS pointer/object policy: `manage-large-files`; ordinary Git object database integrity: `repair-repository-integrity`.
- Initial clone depth/filter choice: `setup-repository`; healthy large-repository tuning: `optimize-large-repository`; broken completeness: `repair-repository-integrity`.

## Package boundaries

Not included as Git-owned skills: general code review, secret scanning, release preparation, provider-specific pull-request/branch-protection administration, and deployment. These may consume Git evidence but have different central decisions, authorization models, and verification surfaces.
