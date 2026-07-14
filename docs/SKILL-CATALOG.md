# Skill Catalog and Scope Boundaries

The catalog is organized by desired postcondition. A normal user journey may activate more than
one skill sequentially, but no two skills should own the same consequential outcome at the same
time.

## Boundary rules

- Diagnosis identifies state and routes; it does not repair.
- Configuration changes behavior; it does not create history.
- Remote topology identifies destinations/refspecs; branch synchronization reconciles one branch.
- Local branch lifecycle does not merge, rebase, push, or manage linked-worktree registrations.
- Integration combines a whole line; transplant copies selected commits.
- Preservation acts before loss; recovery searches after loss.
- Undo reverses known state; recovery discovers unknown state.
- Commit crafting creates new atomic commits; history editing changes existing commit series.
- History investigation answers provenance; regression search executes a good/bad oracle.
- Release preparation changes local release artifacts; tag management changes tag refs/objects.
- LFS/large-file policy is separate from repository performance optimization.
- One-remote maintenance is separate from whole-repository migration.

## `diagnose-repository`

**Outcome:** Build a precise, non-mutating explanation of the repository's current state and route the user to the smallest next workflow.

**Routes here**

- Git reports an unfamiliar state or error and the user does not know what to do next.
- Status and diff appear inconsistent, or a file seems changed, ignored, missing, or untracked.
- HEAD is detached, unborn, missing, or an operation such as merge/rebase/cherry-pick is in progress.
- Repository integrity, shallow-clone, alternates, linked-worktree, or object-availability concerns must be diagnosed.

**Routes elsewhere**

- Use `undo-changes` when the target and reversal are already known.
- Use `recover-lost-work` when commits or files are missing or unreachable.
- Use `resolve-conflicts` when unmerged entries need semantic resolution.
- Do not repair, clean, reset, prune, fetch, or rewrite as part of diagnosis.

**Primary protected state:** refs, index, worktree files, configuration, remotes, and object database

## `setup-repository`

**Outcome:** Produce one usable local repository at a verified destination without overwriting unrelated files or silently weakening repository completeness.

**Routes here**

- Initialize a new repository in an empty or intentionally selected directory.
- Clone a repository, including explicit shallow, partial, bare, mirror, single-branch, or no-checkout variants.
- Choose an initial branch name or verify the default branch after setup.
- Diagnose setup-time destination collisions or incomplete clone requirements.

**Routes elsewhere**

- Use `configure-git` for identity, attributes, hooks, aliases, signing, or policy.
- Use `manage-submodules` for nested repositories.
- Use `optimize-large-repository` for ongoing sparse checkout, maintenance, or performance work.
- Use `migrate-repository` to transfer all refs or change hosting.

**Primary protected state:** pre-existing destination content, global configuration, credentials, unrelated repositories, and remote state

## `configure-git`

**Outcome:** Establish the requested Git behavior at the narrowest valid scope while preserving unrelated configuration and revealing provenance.

**Routes here**

- Set or diagnose author/committer identity, signing, pull/rebase defaults, default branch, diff/merge drivers, aliases, or credential helpers.
- Maintain `.gitignore`, `.gitattributes`, repository-owned hooks, or config includes.
- Explain why local, worktree, global, system, conditional include, or environment configuration wins.
- Configure safe line-ending, filemode, case, symlink, or long-path behavior with platform evidence.

**Routes elsewhere**

- Use `manage-remotes` for remote URLs and refspecs.
- Use `manage-large-files` for LFS tracking and large-object policy.
- Use `craft-commits` to create commits or choose commit-message style.
- Do not place credentials or tokens in config.

**Primary protected state:** unrelated keys, higher/lower scopes, user secrets, repository history, and remote state

## `manage-remotes`

**Outcome:** Make remote topology accurately represent the intended repositories and ref mappings without silently publishing or leaking authentication material.

**Routes here**

- Add, rename, remove, or change a remote and its fetch/push URL.
- Diagnose wrong repository, wrong account, duplicate remotes, asymmetric fetch/push URLs, or unexpected remote-tracking refs.
- Inspect or alter fetch/push refspecs and prune policy.
- Fetch to refresh observations when network access is established and no branch integration is implied.

**Routes elsewhere**

- Use `sync-branches` for ahead/behind reconciliation and ordinary push/pull outcomes.
- Use `migrate-repository` for all-ref transfer or host migration.
- Use `configure-git` for credential-helper selection.
- Do not publish refs or rewrite a remote branch under this skill.

**Primary protected state:** credentials, local branches, worktree/index, unrelated remotes, hosted repositories, and remote branches

## `craft-commits`

**Outcome:** Turn selected local work into the smallest complete, reviewable sequence of commits while preserving unrelated edits and the repository's message convention.

**Routes here**

- Commit all or selected local changes.
- Split a mixed worktree into logical commits or repair accidental staging.
- Amend the current unpublished commit when its target and publication status are established.
- Choose commit messages based on repository policy/history, with a Conventional Commits fallback.

**Routes elsewhere**

- Use `edit-commit-history` to reorder, squash, split, or reword multiple existing commits.
- Use `undo-changes` to unstage or discard known changes without creating a commit.
- Use `scan-secrets` before committing when secret risk is material.
- Do not push, tag, merge, or alter unrelated working changes.

**Primary protected state:** unselected worktree/index content, untracked files, refs other than the intended branch, remotes, and secrets

## `manage-branches`

**Outcome:** Establish the intended local branch/ref state while preserving commits, worktree changes, linked worktrees, and remote refs.

**Routes here**

- Create a branch from an exact start point, switch branches, or attach a detached commit to a name.
- Rename, copy, or delete one local branch.
- Set, change, or remove upstream metadata without pushing.
- Explain branch containment, merged status, or why a branch cannot be switched/deleted.

**Routes elsewhere**

- Use `sync-branches` to update from or publish to a remote.
- Use `integrate-branches` to merge or rebase lines of development.
- Use `manage-worktrees` when a branch is checked out elsewhere.
- Use `edit-commit-history` to rewrite commit topology.

**Primary protected state:** unrelated refs, commits, local changes, linked worktrees, remote refs, and configuration

## `sync-branches`

**Outcome:** Make one local/remote branch relationship reach an explicitly chosen state without losing commits or silently choosing a divergence policy.

**Routes here**

- Update a local branch from its remote counterpart.
- Publish a new branch or push an ordinary fast-forward update.
- Resolve non-fast-forward rejection or 'divergent branches' guidance.
- Set upstream as part of an explicit first push.

**Routes elsewhere**

- Use `manage-remotes` when the destination URL/refspec is wrong.
- Use `integrate-branches` for local merge/rebase decisions not centered on an upstream.
- Use `edit-commit-history` for force-with-lease or published rewrite.
- Use `migrate-repository` for many refs or host transfer.

**Primary protected state:** other refs, unrelated local changes, remote branches, tags, credentials, and published history

## `integrate-branches`

**Outcome:** Create the intended integrated history at an exact local target while preserving contracts, unrelated work, and recoverability.

**Routes here**

- Merge one branch into another, fast-forward a branch, or rebase an unpublished local branch onto a new base.
- Choose merge versus rebase based on publication, policy, topology, and review needs.
- Perform an integration dry run or explain likely commits/conflicts.
- Abort or continue an integration when the primary task is completing that integration rather than resolving individual conflicts.

**Routes elsewhere**

- Use `sync-branches` when the main outcome is local/upstream synchronization and ordinary push.
- Use `transplant-commits` for selected exact commits.
- Use `resolve-conflicts` when unmerged paths require semantic resolution.
- Use `edit-commit-history` for interactive reorder/squash/reword or published rewrite.

**Primary protected state:** unrelated branches, worktree changes, remote refs, tags, and published commits outside scope

## `preserve-work`

**Outcome:** Create a verified, recoverable snapshot of exactly the intended in-progress state while leaving excluded work protected.

**Routes here**

- Save work before switching branches, pulling, rebasing, testing another revision, or handing off.
- Choose among stash, temporary/WIP commit, safety branch, patch, or copied untracked files.
- Restore a previously created preservation artifact when its identity is known.
- Inventory what a stash would and would not include.

**Routes elsewhere**

- Use `recover-lost-work` when work is missing or the preservation artifact is unknown.
- Use `undo-changes` to discard or unstage known state.
- Use `manage-worktrees` when parallel work should remain checked out rather than packed away.
- Do not treat a stash as a durable backup or remote publication.

**Primary protected state:** excluded local work, secrets, unrelated refs, original files, and remote state

## `manage-worktrees`

**Outcome:** Establish the requested linked-worktree topology while protecting every registered worktree, checked-out branch, and uncommitted file.

**Routes here**

- Create a second checkout for another branch or detached commit.
- Explain why a branch is already checked out elsewhere.
- Move, lock, unlock, repair, or remove one exact linked worktree.
- Prune stale registrations only after enumerating the complete candidate set.

**Routes elsewhere**

- Use `manage-branches` for local branch lifecycle within one checkout.
- Use `preserve-work` if the goal is merely to save current changes.
- Use `diagnose-repository` for generic repository discovery.
- Do not use broad prune as a cleanup shortcut.

**Primary protected state:** other worktrees, their local changes, shared refs/objects, unrelated paths, and remote state

## `resolve-conflicts`

**Outcome:** Produce a semantically correct resolved tree, preserve intended behavior from all relevant sides, and complete or safely leave the operation in an explicit state.

**Routes here**

- Files contain conflict markers or the index reports unmerged entries.
- A merge, rebase, cherry-pick, revert, or stash apply stopped for conflicts.
- Rename/delete, directory/file, binary, submodule, or modify/delete conflicts need interpretation.
- The user needs help choosing continue, skip, or abort based on the operation.

**Routes elsewhere**

- Use `integrate-branches` to choose and begin merge/rebase.
- Use `transplant-commits` to choose and begin cherry-pick.
- Use `undo-changes` when the desired outcome is only aborting a known operation.
- Do not resolve by blanket `ours`/`theirs` without contract evidence.

**Primary protected state:** unrelated paths/commits, remote refs, untracked files, and policy-sensitive files

## `undo-changes`

**Outcome:** Reach a specified earlier or inverse state while preserving all material work outside the exact reversal scope.

**Routes here**

- Unstage selected paths while keeping worktree edits.
- Restore selected tracked files from the index or an exact commit.
- Abort a known merge/rebase/cherry-pick/revert/bisect operation.
- Create a revert commit for known changes or reset an unpublished local ref under an explicit keep/mixed/soft/hard policy.

**Routes elsewhere**

- Use `recover-lost-work` when the desired object/version is unknown or missing.
- Use `edit-commit-history` for multi-commit or published rewrite.
- Use `preserve-work` before reversal when current work must be captured.
- Do not use broad hard reset or clean as a generic fix.

**Primary protected state:** unrelated paths, untracked files, unique commits, other refs/worktrees, and remote state

## `recover-lost-work`

**Outcome:** Identify the correct recoverable object with evidence, restore it under a new safe name or path, and avoid destroying remaining recovery evidence.

**Routes here**

- A commit/branch/stash/file seems lost after reset, rebase, deletion, or detached HEAD.
- Find work through reflogs, dangling objects, fsck, ORIG_HEAD, or backup refs.
- Recover an old version of a path when the exact commit is unknown.
- Assess whether garbage collection, shallow history, or missing objects limits recovery.

**Routes elsewhere**

- Use `undo-changes` when the target state is known and reachable.
- Use `preserve-work` before risk, not after loss.
- Use `diagnose-repository` when the issue may be status/index semantics rather than missing content.
- Do not run aggressive prune/gc or overwrite current state during investigation.

**Primary protected state:** current refs/worktree/index, other recovery candidates, reflogs, object database, and remote state

## `transplant-commits`

**Outcome:** Replay exactly the intended logical changes onto the target in a verified order without importing unrelated branch history.

**Routes here**

- Cherry-pick one or more exact commits or a reviewed commit range.
- Move a fix committed on the wrong branch to the intended branch.
- Backport selected patches to a maintenance branch.
- Continue, abort, or assess an empty cherry-pick when the main task is the transplant.

**Routes elsewhere**

- Use `integrate-branches` for a complete branch line.
- Use `edit-commit-history` to reorder/squash/reword commits already on the target.
- Use `resolve-conflicts` for deep semantic conflict work.
- Do not assume cherry-pick always produces a different object ID.

**Primary protected state:** source refs, unrelated target changes, remote refs, tags, and omitted commits

## `edit-commit-history`

**Outcome:** Produce the explicitly designed replacement commit series while preserving content, recovery anchors, signatures/policy, and concurrent remote work.

**Routes here**

- Interactive rebase for reorder, squash/fixup, drop, reword, or edit/split.
- Rewrite a published branch only under explicit authorization and exact remote lease.
- Repair commit structure before review or merge.
- Assess signature loss, changed OIDs, downstream impact, and recovery.

**Routes elsewhere**

- Use `craft-commits` for new commits or a simple unpublished tip amend.
- Use `integrate-branches` for routine local rebase/merge onto a base.
- Use `migrate-repository` for repository-wide filter/rehosting work.
- Use `undo-changes` for a known reset/revert without series editing.

**Primary protected state:** unrelated refs, concurrent remote commits, working changes, tags/notes not explicitly in scope, and secrets

## `investigate-history`

**Outcome:** Produce an evidence-backed history explanation with exact commits, paths, ranges, and limitations.

**Routes here**

- Find the commit that added, removed, renamed, or changed specific text or behavior.
- Trace a path across renames or inspect merge ancestry and first-parent history.
- Explain who last changed lines while accounting for moves, copies, or generated code.
- Compare whether a patch was applied, reverted, or independently recreated.

**Routes elsewhere**

- Use `find-regression` when a reproducible good/bad test can locate a causal boundary.
- Use `review-change-set` to assess correctness of a proposed diff.
- Use `recover-lost-work` when the goal is to restore missing objects.
- Do not alter refs, files, or remote state.

**Primary protected state:** refs, index, worktree, configuration, and remote state

## `find-regression`

**Outcome:** Identify a minimal causal boundary with a trustworthy test oracle and leave the repository in a known state.

**Routes here**

- Run manual or automated `git bisect` between verified good and bad revisions.
- Design a classifier that distinguishes good, bad, skip, and infrastructure failure.
- Handle builds, generated artifacts, dependencies, submodules, or environment setup across revisions.
- Validate the reported first bad commit and nearby boundary.

**Routes elsewhere**

- Use `investigate-history` for text/provenance questions without an executable oracle.
- Use `review-change-set` to inspect a known diff.
- Use `diagnose-repository` when current repository state itself is confusing.
- Do not patch the regression as part of the search unless separately requested.

**Primary protected state:** original branch/worktree changes, refs, remotes, and external services/data

## `review-change-set`

**Outcome:** Produce prioritized, actionable findings tied to exact changed lines and affected contracts, with no unsupported claims or hidden repository mutation.

**Routes here**

- Review a pull-request branch, commit range, staged changes, or patch.
- Assess a diff for bugs, missing tests, compatibility or security regressions.
- Explain the effective change relative to the correct base/merge base.
- Run focused checks in an isolated disposable environment when justified.

**Routes elsewhere**

- Use a repository-specific review skill if the task is exclusively style or a specialized domain.
- Use `investigate-history` for provenance rather than defect review.
- Use implementation skills to apply fixes.
- Do not review an unbounded entire repository under this skill.

**Primary protected state:** target repository refs/index/worktree/config, remote state, secrets, and unrelated files

## `scan-secrets`

**Outcome:** Identify credible secret exposures with minimum data handling, safe fingerprints, exact locations, and a bounded remediation route.

**Routes here**

- Scan worktree, index, commit range, or repository history for secret-like material.
- Review a scanner finding and distinguish real credential, test fixture, hash, or false positive.
- Check whether a secret entered a commit or published history.
- Prepare containment steps and route rotation/history remediation.

**Routes elsewhere**

- Use provider/security operations to rotate or revoke credentials.
- Use `edit-commit-history` or migration tooling for authorized removal from history.
- Use `craft-commits` only after the secret risk is cleared.
- Do not print, copy, transmit, or deterministically hash raw low-entropy secrets.

**Primary protected state:** secret values, unrelated files/history, external providers, refs, and remote state

## `manage-submodules`

**Outcome:** Make the superproject's gitlink, `.gitmodules`, local submodule config, nested checkout, and expected remote relationship consistent.

**Routes here**

- Add or remove a submodule.
- Initialize/update recursive submodules or switch their tracked branch policy.
- Diagnose detached submodule HEAD, dirty submodule state, missing commit, changed URL, or nested recursion.
- Move a submodule path or repair synchronization after `.gitmodules` changes.

**Routes elsewhere**

- Use `manage-remotes` for the superproject's remotes.
- Use `setup-repository` for a normal standalone clone.
- Use `integrate-branches` for Git subtree or branch integration if that is the chosen model.
- Do not commit nested repository content as ordinary files accidentally.

**Primary protected state:** nested uncommitted work, unrelated submodules, credentials, superproject history, and remote refs

## `manage-large-files`

**Outcome:** Make selected large-file paths use the intended storage policy and remain retrievable without losing binary content or silently rewriting unrelated history.

**Routes here**

- A push is rejected because a file or object is too large.
- Add, change, or remove Git LFS tracking for selected patterns.
- Diagnose an LFS pointer where content should be, missing objects, smudge failures, or clone checkout issues.
- Plan a bounded migration of exact paths into or out of LFS.

**Routes elsewhere**

- Use `optimize-large-repository` for sparse checkout, partial clone, maintenance, or general scale performance.
- Use `edit-commit-history` for small local series rewriting unrelated to LFS.
- Use `migrate-repository` for whole-host transfer.
- Do not delete large files or rewrite all history merely to satisfy a push error.

**Primary protected state:** unrelated paths/refs, raw binary originals until verification, credentials, and external storage outside scope

## `optimize-large-repository`

**Outcome:** Reduce measured Git latency or transfer/storage cost while preserving correctness, required files/history, and recoverability.

**Routes here**

- Clone/status/checkout/fetch/log operations are slow in a large monorepo.
- Configure or diagnose sparse checkout and sparse index.
- Choose partial clone filters or maintenance tasks.
- Inspect object/pack/ref scale and schedule safe optimization.

**Routes elsewhere**

- Use `manage-large-files` for host size limits or LFS.
- Use `setup-repository` for first-time clone choice when no repository exists yet.
- Use `diagnose-repository` for correctness symptoms not shown to be performance-related.
- Do not run aggressive gc/prune or delete worktrees/refs as a generic optimization.

**Primary protected state:** required paths/history/objects, recovery evidence, other worktrees, user config outside scope, and remotes

## `prepare-release`

**Outcome:** Produce a reviewable, reproducible local release candidate whose version, artifacts, notes, and verification agree.

**Routes here**

- Bump a version and update all authoritative mirrors.
- Prepare changelog/release notes from an exact commit range.
- Regenerate and verify release artifacts or lockfiles.
- Create a release preparation commit and readiness report.

**Routes elsewhere**

- Use `manage-tags` to create or verify a tag.
- Use deployment/package-specific workflows to publish artifacts.
- Use `craft-commits` for ordinary non-release commits.
- Do not push, upload, create hosted releases, or modify production.

**Primary protected state:** unrelated changes, tags, remote refs, registries, deployments, credentials, and production state

## `manage-tags`

**Outcome:** Establish the exact requested tag object/ref locally or at a verified remote with correct type, target, annotation, signature, and immutability policy.

**Routes here**

- Create a lightweight, annotated, or signed tag at an exact object.
- Verify tag signature, annotation, tagger, object type, and peeled target.
- Publish or delete one exact remote tag when explicitly authorized.
- Assess an existing tag for idempotence or conflict.

**Routes elsewhere**

- Use `prepare-release` for version/changelog/artifact work.
- Use `sync-branches` for branches.
- Use package/deployment workflows for hosted releases or publication.
- Do not silently move a published tag.

**Primary protected state:** other tags/refs, release files, branches, packages, credentials, and deployments

## `migrate-repository`

**Outcome:** Transfer the explicitly selected repository state to a verified destination with auditable completeness, no credential leakage, and a controlled cutover/recovery plan.

**Routes here**

- Mirror all intended branches/tags/notes or a declared ref subset to a new host.
- Migrate Git LFS objects and validate submodule/repository dependencies.
- Change hosting with default branch, permissions, branch/tag policy, and collaborator cutover.
- Perform a repository-wide filter only when required by the migration postcondition.

**Routes elsewhere**

- Use `manage-remotes` to add/change one remote.
- Use `sync-branches` to push one ordinary branch.
- Use `setup-repository` for a development clone.
- Use provider-specific tooling for issues/PRs/wiki/releases unless explicitly included and supported.

**Primary protected state:** out-of-scope destination refs/data, credentials, source availability, unrelated repositories, and external integrations
