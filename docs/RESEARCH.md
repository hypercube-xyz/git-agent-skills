# Research Basis

This repository was designed from current Git documentation, common user failure modes, and
successful public Agent Skill packages. Research was performed before defining the catalog so that
skills route from real symptoms rather than merely mirroring command names.

## Primary Git sources

- Git reference documentation: <https://git-scm.com/docs/git>
- Pro Git book: <https://git-scm.com/book/en/v2>
- Git worktree: <https://git-scm.com/docs/git-worktree>
- Git rerere: <https://git-scm.com/docs/git-rerere>
- Git reflog: <https://git-scm.com/docs/git-reflog>
- Git fsck: <https://git-scm.com/docs/git-fsck>
- Git bundle: <https://git-scm.com/docs/git-bundle>
- Git sparse-checkout: <https://git-scm.com/docs/git-sparse-checkout>
- Git partial clone design: <https://git-scm.com/docs/partial-clone>
- Git maintenance: <https://git-scm.com/docs/git-maintenance>
- Git submodule: <https://git-scm.com/docs/git-submodule>
- Git tag and verification: <https://git-scm.com/docs/git-tag>
- GitHub non-fast-forward guidance:
  <https://docs.github.com/en/get-started/using-git/dealing-with-non-fast-forward-errors>
- GitHub merge-conflict guidance:
  <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts>
- GitHub large-file and LFS guidance:
  <https://docs.github.com/en/repositories/working-with-files/managing-large-files>
- Conventional Commits: <https://www.conventionalcommits.org/en/v1.0.0/>

## Recurrent user pain points

The catalog explicitly covers recurring questions that often begin with symptoms rather than a
known Git operation:

- non-fast-forward push and divergent pull;
- accidentally committing on the wrong branch;
- detached HEAD and unreachable commits;
- reset/rebase/branch-deletion recovery;
- staged versus unstaged confusion;
- untracked files blocking checkout/merge;
- line-ending, filemode, case-only rename, symlink, and long-path behavior;
- interrupted merge/rebase/cherry-pick and operation-specific conflict semantics;
- stale worktree registrations;
- submodule detached state and unavailable gitlink commits;
- large-file rejection, LFS pointer/object failures, and repository-scale performance;
- release tag type, peeling, signing, and immutable publication;
- migration completeness beyond branches and tags.

High-traffic public troubleshooting threads were used as demand signals, not as authoritative
technical specifications. Final procedures are grounded in current Git and hosting documentation.

## Public skill-repository observations

Reviewed repositories include:

- Agent Skills specification: <https://agentskills.io/>
- Vercel Skills CLI: <https://github.com/vercel-labs/skills>
- Anthropic skills examples: <https://github.com/anthropics/skills>

Useful patterns retained:

- descriptions act as routing contracts and include near-miss boundaries;
- a skill should have one coherent outcome and a deliberately narrow review surface;
- long conditional knowledge belongs in directly linked references;
- explicit plugin catalogs improve package navigation;
- deterministic scripts are appropriate for mechanical safety and validation;
- repository-maintenance rules should keep the manifest, README, and filesystem catalog aligned;
- claims about productivity require comparative execution evidence rather than package structure.

Patterns deliberately avoided:

- a skill per individual command;
- duplicate skills that differ only by terminology;
- generic doctrine occupying most of every `SKILL.md`;
- routing fixtures written only in expert Git vocabulary;
- treating a successful command as proof of the desired postcondition;
- claiming support for every model/runtime without execution evidence.

## Catalog derivation

The 25 skills are separated by postcondition:

- inspection versus mutation;
- topology configuration versus branch synchronization;
- full-line integration versus selected-commit transplant;
- proactive preservation versus post-loss recovery;
- known reversal versus historical rediscovery;
- new commit construction versus editing existing commit history;
- release preparation versus tag lifecycle;
- large-file storage policy versus large-repository performance;
- one-remote maintenance versus full repository migration.

This separation minimizes overlapping activation while preserving normal end-to-end workflows in
which one skill routes to another after its own postcondition is complete.
