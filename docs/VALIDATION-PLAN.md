# Validation plan

Validation applies to the exact source, tools, model/runtime, and scenarios exercised. A passing package check does not certify future agent behavior.

## Package and routing contracts

`scripts/validate_skills.py` checks catalog/plugin/filesystem/README parity, required sections, directly triggered resources, fixture coverage, known routing intersections, and lexical overlap signals. The overlap check calls for human review; it cannot prove semantic ownership.

`tests/routing.json` and `tests/scenarios.json` are static inventories. The latter records observable assertions for stale-state, partial-failure, and prompt-injection cases; the validator checks their structure and coverage, not an agent's decisions. Do not describe a static pass as an execution evaluation.

## Git and package semantics

`scripts/smoke_test_git.py` uses disposable repositories to test Git and package mechanics, including leases, conflict state, recovery, worktrees, mailbox replay, remote redaction, and release inputs. A platform subset includes portable tests plus the selected platform cases. Record Git/Python/OS versions and skips; an environment-dependent skip limits the claim.

`scripts/security_regression.py` checks security contracts and helper behavior. A failed platform privilege prerequisite must be reported separately from a code failure and resolved by CI or another supported environment before making a cross-platform claim.

The destination-safety fixture uses a real directory junction on Windows, which does not require symlink privileges, and a real directory symlink elsewhere. Both the path validator and release CLI must reject the redirected destination without writing artifacts; normal paths remain accepted. Fixture creation errors fail the check rather than skipping it.

`scripts/review_regressions.py` exercises the reviewed helper defects and Git controls in disposable repositories, including paired unsafe/safe variants. Its fixtures preserve intentional configuration overrides rather than allowing the maintenance wrapper to hide fsmonitor or replacement behavior. These checks verify command mechanics and retained state; they do not execute skill prose or certify an agent's decisions.

`scripts/recheck_regressions.py` checks optional index writes, copied branch policy, notes/autostash effects, attached-worktree ref correction, and symbolic-ref dereferencing in disposable repositories. Its isolated fixture environment deliberately permits optional index refresh so the negative control can expose the effect. Reference-kind checks are separate from `--no-deref`, which prevents target mutation but does not by itself enforce a direct-ref precondition. These are Git behavior checks, not blind agent evaluations.

## Agent execution evidence

Before release, run a risk-based selection of blind tasks with raw disposable repositories and the installed v2 skills. Prioritize routine routes, near-boundary ambiguity, unrelated staged/untracked work, conflicts and sequencer continuation, unborn/bare/partial states, remote endpoint splits, stale refs, partial publication, and untrusted content according to what static and mechanical checks leave uncertain. Inspect tool traces and final refs/index/worktree/remote state against independent assertions, including protected effects. Repeat cases that reveal a skill defect after repair; record unexercised paths as limits, not passes.

Record exact skill source, model/runtime, prompt, repository fixture, tool trace, checks, outcome, failure, and limits. Preserve the v1.2.1 routing pilot as historical evidence only; it measured routing on one model/runtime, not v2 Git execution. A small blind pass supports only the paths it exercised.

`tests/agent-execution/run.py <new-evidence-directory>` invokes the installed Codex CLI
with its configured account/model for 12 independent tasks. It retains a skill snapshot,
per-file hashes, exact prompts, raw JSONL, runtime and process results, and independent
protected-state checks. This consumes normal model usage and is intentionally separate
from deterministic CI; inspect the raw trace for intermediate effects and unnecessary
stops. [The 2026-10-18 run](../tests/agent-execution/2026-10-18.md) passed the 12 task
oracles but exposed tool-created `.serena/` files, including in the read-only task.
It is bounded execution evidence, not a production-readiness certificate.

## Release gate

CI runs structural, Git semantic, security, client-discovery, and clean-checkout checks separately. `scripts/build_release.py` is a pure packager: it reads files from the committed revision through `git ls-tree` and `git cat-file`, rejects unsupported entries, and creates a deterministic ZIP plus checksum and metadata sidecars. `--check` builds archive bytes twice in-process; it does not run validators or prove cross-environment reproducibility. The builder records validation as separately performed by CI, never as a check it ran itself.

The release workflow validates the tag, tests the checked-out revision, then builds and uploads the package. Each sidecar is atomically written, but the three-file set is not transactional; rerunning the deterministic builder reconciles an interrupted set. After publication, verify the tag's commit, workflow result, release asset names, and downloadable checksums before calling the release complete.

Pinned Skills CLI and Claude Code client checks are blocking in CI. The latest-client forward probe is non-blocking and is not release evidence for its version.

Before serialization, the builder checks the committed plugin version against the committed
catalog. Release CI passes `--release-tag` to require the exact `v<package_version>` tag in
both jobs; the first gate uses `--validate-only` before tests or artifact creation. Metadata
version and tag are derived from that validated catalog. Negative tests cover mismatched
tags, mismatched/missing plugin versions, and absence of serialization/writes on rejection.
The blocking minimum-Git job uses checksum-pinned Git 2.35.0 and fails unsupported skips;
verified safe refusals are reported separately from supported operations.

Release identity validation precedes a call to the same `validate.yml` workflow used for
pull requests, evaluated at the caller's source revision. Publication depends on that
complete workflow, including blocking pinned Skills CLI/Claude Code checks, workflow lint,
the OS matrix, minimum Git and reproducible packaging. Packaging explicitly depends on
lint, OS tests and minimum Git. The optional latest-client probe does not run for release
tags and is not a release gate. Artifact attestations are not implemented.

`scripts/test_file_safety.py` constructs Git trees directly so file/directory case collisions
are exercised even on Windows. Its disposable installer checks cover original-manifest
upgrades, local additions/edits/deletions, empty directory changes, legacy/corrupt manifests,
all-target refusal, and rollback after a deep edit between preflight and replacement.
