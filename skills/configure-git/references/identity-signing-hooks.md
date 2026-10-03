# Identity, signing, and executable configuration

Read this when multiple identities, conditional includes, signing, hooks, or credential-adjacent settings affect the requested behavior.

## Identity resolution

Inspect `user.name`, `user.email`, `user.useConfigOnly`, relevant environment variables, and all applicable `includeIf` files with scope and origin. The same key can be multi-valued or overridden by a later scope. Verify `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` in each affected repository/worktree under the intended environment; a config file merely existing does not prove its condition matched.

Prefer a path or remote condition only when the matching boundary is stable and testable. Before unsetting a local value, determine which inherited value will become effective. A future identity fix does not alter existing commit objects; route any requested rewrite separately.

## Signing

Establish required format, key selector, trust model, and repository/host policy before changing `commit.gpgSign`, `tag.gpgSign`, `user.signingKey`, or SSH signing settings. Do not display private key material, sockets, or credential-helper contents. Create a disposable signed object only in an authorized location, then verify with the intended verifier and authorized signer policy; successful creation alone does not establish trust.

## Hooks and other programs

Inspect `core.hooksPath`, repository-managed hook tooling, executable permissions, dependencies, network behavior, secret access, and index/worktree mutations. A local hook can alter the content to be committed. Preserve required hooks and signing behavior; do not install hidden global hooks or bypass policy to complete another task. Test the relevant command in the actual worktree/environment and verify the hook's effects and unrelated commands.

Filters, external diff/merge drivers, credential helpers, URL rewrites, aliases, pagers, editors, and signing programs also select executable behavior. A Git config override can disable a program but is not process or filesystem isolation; stop if the required boundary cannot be enforced.
