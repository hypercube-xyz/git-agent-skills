# Reversal matrix

| Goal | Typical mechanism | Ref | Index | Worktree |
|---|---|---:|---:|---:|
| Unstage paths | `git restore --staged -- <paths>` | unchanged | from HEAD | unchanged |
| Discard tracked worktree edits | `git restore --worktree -- <paths>` | unchanged | unchanged | from index |
| Keep changes staged while moving HEAD | `git reset --soft <target>` | moves | unchanged | unchanged |
| Keep changes unstaged while moving HEAD | `git reset --mixed <target>` | moves | from target | unchanged |
| Move HEAD and tracked files | `git reset --hard <target>` | moves | from target | from target |
| Preserve public history | `git revert <commit>` | new commit | new tree | new tree |

Do not use the table without inspecting current state. A non-obstructing untracked path normally
survives `reset --hard`, but an untracked file or directory that blocks a path required by the target
tree can be deleted. Inventory those collisions before reset. `git clean` remains a separate action
with its own preview and confirmation requirements.

For a known interrupted operation, use its matching abort command only after verifying the
operation type. A stale-looking marker should not be removed manually as a first response.

## Path and output safety

When paths or ref names can be user-controlled, pass command arguments as arrays rather than shell-concatenated strings, use `--` before pathspecs, and use NUL-delimited output (`-z`) for machine parsing. Do not split filenames on whitespace or newlines. Test names beginning with `-`, whitespace/newlines, Unicode, symlinks, nested repositories, and case-collision scenarios where the platform permits them.
