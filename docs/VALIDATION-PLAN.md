# Validation plan

Validation applies to the exact source, tools, model/runtime, and scenarios exercised. A passing package check does not certify future agent behavior.

## Package and routing contracts

`scripts/validate_skills.py` checks catalog/plugin/filesystem/README parity, required sections, directly triggered resources, fixture coverage, known routing intersections, and lexical overlap signals. The overlap check calls for human review; it cannot prove semantic ownership.

`tests/routing.json` and `tests/scenarios.json` are static inventories. The latter records observable assertions for stale-state, partial-failure, and prompt-injection cases; the validator checks their structure and coverage, not an agent's decisions. Do not describe a static pass as an execution evaluation.

## Git and package semantics

`scripts/smoke_test_git.py` uses disposable repositories to test Git and package mechanics, including leases, conflict state, recovery, worktrees, mailbox replay, remote redaction, and release inputs. A platform subset includes portable tests plus the selected platform cases. Record Git/Python/OS versions and skips; an environment-dependent skip limits the claim.

`scripts/security_regression.py` checks security contracts and helper behavior. A failed platform privilege prerequisite must be reported separately from a code failure and resolved by CI or another supported environment before making a cross-platform claim.

## Agent execution evidence

Before release, run a risk-based selection of blind tasks with raw disposable repositories and the installed v3 skills. Prioritize routine routes, near-boundary ambiguity, unrelated staged/untracked work, conflicts and sequencer continuation, unborn/bare/partial states, remote endpoint splits, stale refs, partial publication, and untrusted content according to what static and mechanical checks leave uncertain. Inspect tool traces and final refs/index/worktree/remote state against independent assertions, including protected effects. Repeat cases that reveal a skill defect after repair; record unexercised paths as limits, not passes.

Record exact skill source, model/runtime, prompt, repository fixture, tool trace, checks, outcome, failure, and limits. Preserve the v1.2.1 routing pilot as historical evidence only; it measured routing on one model/runtime, not v3 Git execution. A small blind pass supports only the paths it exercised.

## Release gate

CI runs structural, Git semantic, security, client-discovery, and clean-checkout checks separately. `scripts/build_release.py` is a pure packager: it reads files from the committed revision through `git ls-tree` and `git cat-file`, rejects unsupported entries, and creates a deterministic ZIP plus checksum and metadata sidecars. `--check` builds archive bytes twice in-process; it does not run validators or prove cross-environment reproducibility. The builder records validation as separately performed by CI, never as a check it ran itself.

The release workflow validates the tag, tests the checked-out revision, then builds and uploads the package. Each sidecar is atomically written, but the three-file set is not transactional; rerunning the deterministic builder reconciles an interrupted set. After publication, verify the tag's commit, workflow result, release asset names, and downloadable checksums before calling the release complete.

Pinned Skills CLI and Claude Code client checks are blocking in CI. The latest-client forward probe is non-blocking and is not release evidence for its version.
