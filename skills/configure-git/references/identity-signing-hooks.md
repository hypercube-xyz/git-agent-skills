# Multi-identity, signing, and hooks

## Identity routing

- Inspect `user.name`, `user.email`, `user.useConfigOnly`, environment overrides, and all conditional includes with origin/scope.
- Prefer path- or remote-derived `includeIf` rules only when the matching boundary is stable and testable.
- Verify from every affected repository; a config file existing is not evidence that its condition matched.
- Do not rewrite existing commits merely to fix future identity unless history editing is separately in scope.

## Signing

- Establish the required signing format, key selector, trust model, and repository/host policy before changing `commit.gpgSign`, `tag.gpgSign`, `user.signingKey`, or SSH signing settings.
- Do not print private key material, agent sockets, or credential-helper contents.
- Test a disposable signed object and verify the signature with the intended verifier. Creation success alone does not establish trust.

## Hooks

- Inspect `core.hooksPath`, repository-managed hook tooling, executable permissions, shell/runtime dependencies, network access, secret handling, and mutation behavior.
- Hooks are policy-sensitive executable state. Disclose their future effects and do not install hidden global hooks to make another task pass.
- Verify invocation under the actual worktree/environment and confirm unrelated commands are not intercepted.
