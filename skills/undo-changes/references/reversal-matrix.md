# Reversal matrix

| Goal | Typical mechanism | Ref | Index | Worktree |
|---|---|---:|---:|---:|
| Unstage paths | `git restore --staged -- <paths>` | unchanged | from HEAD | unchanged |
| Discard tracked worktree edits | `git restore --worktree -- <paths>` | unchanged | unchanged | from index |
| Keep changes staged while moving HEAD | `git reset --soft <target>` | moves | unchanged | unchanged |
| Keep changes unstaged while moving HEAD | `git reset --mixed <target>` | moves | from target | unchanged |
| Move HEAD and tracked files | `git reset --hard <target>` | moves | from target | from target |
| Preserve public history | `git revert <commit>` | new commit | new tree | new tree |

Do not use the table without inspecting current state. Untracked files are not covered by restore or
reset in the same way; `git clean` has its own preview and confirmation requirements.

For a known interrupted operation, use its matching abort command only after verifying the
operation type. A stale-looking marker should not be removed manually as a first response.
