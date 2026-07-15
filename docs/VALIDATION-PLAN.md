# Validation plan

Validation applies to the exact source, tools, and scenarios exercised. It does not certify every future agent/runtime/environment combination.

## Package, routing, and overlap contract

`scripts/validate_skills.py` checks:

- catalog, plugin, filesystem, README, and tier parity,
- required skill sections, direct triggers for every bundled reference and script,
- missing, orphaned, chained, or duplicated references and untriggered skill-local scripts,
- exact routing/scenario coverage for every catalogued skill,
- unknown, removed, missing, or duplicated fixture entries,
- at least three positive and two negative routing cases per skill,
- realistic skill-specific stale-state, partial-failure, and prompt-injection contract scenarios per skill,
- duplicate objectives and high-overlap skill pairs without explicit routing boundaries,
- reciprocal boundaries for known high-risk intersections.

Lexical overlap is only a review signal. A failure means the package needs a human ownership/routing review; a pass does not prove semantic non-overlap for every possible request.

The scenario file is a static contract inventory. It records prompts and observable assertions that an external runner should evaluate, but the repository validator only checks fixture quality and coverage. A static pass must not be reported as an agent-runtime evaluation.

## Git and package semantics

`scripts/smoke_test_git.py` creates disposable repositories and executes focused cases for desired effects and protected-state/prohibited-effect boundaries. It covers the v1.0.0 semantic surfaces plus mailbox replay, shallow/partial completeness repair, object-corruption containment, branch-stack restacking, subtree/vendor synchronization, and multi-identity/signing/hooks.

A skipped environment-dependent test is reported; zero skips is preferred for release evidence.

## Release gate

`scripts/build_release.py` runs both validators, requires a clean committed tracked tree, selects regular files from the Git index, rejects symlinks/unmerged entries/unsupported modes, creates a deterministic ZIP with one embedded manifest, and emits SHA-256 and sidecar metadata. `--skip-validation` remains truthfully represented in the sidecar.

CI checks grouped skill discovery and the Claude Code plugin manifest with pinned clients on Node 24 for pull requests, pushes to `main`, and manual runs. A separate Node 26/latest-client job runs only after non-PR builds, is non-blocking, and is not release evidence for a pinned client version.

Independent model comparisons are intentionally not stored as source files. Run them in an authorized evaluation environment and retain the results as CI or experiment artifacts rather than package runtime content.
