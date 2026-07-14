# Configuration precedence and portability

Inspect configuration with provenance:

```sh
git config --show-origin --show-scope --get-all <key>
git config --list --show-origin --show-scope
```

Relevant sources include system, global, local, worktree, command-line `-c`, environment, and
conditional includes. A displayed effective value can hide additional values that matter.

## Common portability traps

- `core.autocrlf` is not a substitute for a reviewed `.gitattributes` policy.
- `core.fileMode`, `core.ignoreCase`, and `core.symlinks` reflect filesystem capability and can
  make status output surprising.
- `safe.directory` is a trust exception; do not add broad wildcards to silence ownership errors.
- Commit identity and cryptographic signing are separate controls.
- Hooks are executable policy-sensitive state. Inspect source, arguments, environment, network
  access, and failure behavior before enabling them.
- Aliases can invoke shell commands with `!`; treat them as executable code.

Prefer repository-owned, reviewable policy for team behavior and user-scoped configuration for
personal identity or UI preferences.
