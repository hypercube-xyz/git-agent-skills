# Linked-worktree safety

Inspect machine-readable registrations:

```sh
git worktree list --porcelain -z
```

Each entry may contain `worktree`, `HEAD`, `branch`, `detached`, `locked`, and `prunable` records.
Do not infer safety from directory existence alone.

## Prune rule

```sh
git worktree prune --dry-run --verbose
```

The command has no exact-path selector. Run the real prune only when the entire eligible set is
enumerated and every candidate is authorized. Otherwise repair/remove a specific worktree or wait
for unavailable storage.

Removal should normally use `git worktree remove <exact-path>` after a clean-state check. Avoid
manual deletion because shared administrative records can remain inconsistent.
## Path and output safety

When paths or ref names can be user-controlled, pass command arguments as arrays rather than shell-concatenated strings, use `--` before pathspecs, and use NUL-delimited output (`-z`) for machine parsing. Do not split filenames on whitespace or newlines. Test names beginning with `-`, whitespace/newlines, Unicode, symlinks, nested repositories, and case-collision scenarios where the platform permits them.

