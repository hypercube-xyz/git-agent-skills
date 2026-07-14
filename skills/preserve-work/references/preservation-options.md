# Preservation options

| Need | Preferred form | Important limitation |
|---|---|---|
| Short local context switch | stash | untracked/ignored content requires explicit inclusion |
| Durable Git-native checkpoint | temporary commit on a safety branch | becomes repository history and may trigger hooks |
| Reviewable tracked delta | patch | does not capture untracked files or all metadata |
| Exact committed object closure | bundle with explicit refs | does not capture dirty worktree files |
| Arbitrary untracked/ignored files | restrictive filesystem archive/copy | outside Git integrity model |

Never use `git bundle --all` by habit. Name only the refs required by the preservation
postcondition. For patches, write to a new file outside the affected worktree, fail if it already
exists, and set restrictive permissions.

A stash application can conflict. Keep the stash entry until restoration is verified; do not use a
destructive pop as the first recovery attempt when the state is valuable.
