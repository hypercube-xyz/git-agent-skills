# Changelog

## 1.2.0 - 2026-07-21

- Add SECURITY-EXECUTION.md contract, inject untrusted-content and executable-Git boundary into all 24 skills, and harden mailbox ingestion.
- Add controlled_git_env with ambient config/credential isolation, staged per-destination installer promotion with invocation rollback, and deterministic security regression checks.
- Harden release build: immutable committed blobs, atomic per-file writes, portable path validation, symlink-component rejection.
- Make build_release.py a pure packager — remove validation orchestration; CI runs validators before calling builder.
- Add cross-platform CI: blocking tests on Linux, macOS, and Windows; release publication on Linux only.
- Add --mode auto/symlink/copy to link_skills.py with Windows copy fallback and rollback.
- Fail closed on existing release asset digest mismatch instead of automatic clobber.
- Treat PATH as trusted input for Git executable discovery; document the contract in resolve_git().
- Add platform-specific trusted symlink allowlist with target verification (macOS only).
- Fix linker symlink check to inspect raw path before resolve().

## 1.1.0 - 2026-07-16

- Make bundled script discovery explicit and validate every skill-local script trigger by exact relative path.
- Replace generic scenario templates with skill-specific static contract cases and state clearly that they are not agent-runtime evaluations.
- Clarify the durable-commit versus temporary-rescue boundary between `craft-commits` and `preserve-work`.
- Remove twenty tiny references whose guidance belongs in `SKILL.md`; retain twelve conditional playbooks with direct triggers.
- Remove the undiscoverable top-level handoff document and place mutation-handoff output requirements in the skills that cross consequential boundaries.
- Test Python 3.12 and 3.14 on Ubuntu 26.04 in CI, and distinguish declared Git compatibility targets from observed build versions.
- Bind release provenance to the exact committed source revision while retaining the official v1.0.0 base revision and deterministic source-tree digest.
- Prevent bytecode writes during semantic tests and add normal command-line help/list handling.
- Validate pinned packaging clients on Node 24 and run a non-blocking Node 26/latest-client forward-compatibility probe.
- Preserve credential-free local and file remote destination identity while continuing to fail closed for unclassified URL formats.

- Base the derivative package explicitly on official release `v1.0.0` at commit `1d513f5b29332c406c33705c42ccec6dfaf86e3c`.
- Add `repair-repository-integrity` for corrupt or missing ordinary Git objects, packs, refs, alternates, and broken shallow/partial-clone completeness.
- Add compact/optional `manage-stacked-branches` for dependent review-branch DAGs and coordinated exact-lease publication.
- Fold common multi-skill workflows into direct references of the owning skills instead of adding an umbrella workflow skill or undiscoverable top-level recipes.
- Add focused references for patch/mailbox replay, shallow/partial-clone repair, subtree/vendor synchronization, and multi-identity/signing/hooks.
- Add exact package/catalog/plugin/README/fixture parity validation and integrated overlap/routing checks.
- Preserve the v1.0.0 Git-index release-input model, tracked-symlink rejection, and clean-state gate; generate a deterministic archive with source revision, source-tree identity, artifact hash, and validation status in `git-agent-skills-<version>.release.json`.
- Extend semantic tests for the new skills and references while retaining the v1.0.0 release, remote, recovery, conflict, tag, submodule, installer, and pathological-path cases.
- Keep model evaluation outputs outside the source package; the repository validates deterministic routing, boundary, Git, and packaging behavior.

## 1.0.0 - 2026-07-15

- Introduce a non-overlapping catalog of evidence-driven Git workflow skills.
- Add symptom-driven routing fixtures, boundary scenarios, deterministic validators, and Git semantic smoke tests.
- Add explicit plugin catalog grouping for compatible skill installers.
- Add path-specific external and critical-impact controls for history rewrite, migration, tags, branch publication, destructive reversal, configuration, and LFS migration.
- Add exact force-with-lease and post-publication remote verification requirements.
- Add safe clean/reset ladders, shared-tag-namespace prune warnings, NUL-safe worktree parsing, and pathological path handling guidance.
- Focus the package on Git-owned workflows and document boundaries for code review, secret scanning, and repository-specific release preparation.
- Add catalog groups, compatibility documentation, cross-skill handoff rules, security reporting, stronger routing/scenario fixtures, a fail-closed remote inspection helper, and transactional local skill linking.
- Add deterministic embedded package manifests and sidecar release records containing source-tree identity, build environment, validation status, and artifact hash.
- Fix dynamic CI skill counting, truthful skipped-validation metadata, installer rollback, dotted/slashed remote-name inspection, submodule summary commands, bisect oracle semantics, hard-reset obstruction guidance, exact tag leases, history-fetch scope, and tier wording.
- Package releases from Git-tracked regular files only, reject tracked symlinks, use Git-index modes, and isolate malformed remote URLs without aborting the complete inventory.
