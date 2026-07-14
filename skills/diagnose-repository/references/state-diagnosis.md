# Repository-state diagnosis

Use this reference only for ambiguous state classification.

## Read the layers separately

1. **Object database** — commits, trees, blobs, annotated tags.
2. **Refs and HEAD** — named pointers and the current symbolic or detached position.
3. **Index** — the proposed next tree, including conflict stages and flags.
4. **Worktree** — checked-out files, including untracked and ignored content.
5. **Operation state** — merge, rebase, cherry-pick, revert, bisect, or sequencer metadata.
6. **Topology modifiers** — linked worktrees, submodules, sparse checkout, shallow or partial clone.

## High-value probes

```sh
git rev-parse --show-toplevel --git-dir --git-common-dir
git status --porcelain=v2 --branch
git symbolic-ref -q HEAD || git rev-parse --verify HEAD
git ls-files --stage --debug -- <path>
git worktree list --porcelain
git rev-parse --is-shallow-repository
```

Run `git fsck` only when missing/corrupt objects or reachability are material; it can be costly and
its dangling-object output is not automatically evidence of corruption.

## Common traps

- `git diff` compares worktree to index; `git diff --cached` compares index to HEAD.
- An unborn branch has no commit for `HEAD^{commit}`.
- Detached HEAD is not data loss, but new commits can become unreachable after moving away.
- `assume-unchanged` is a performance hint, not an ignore mechanism.
- `skip-worktree` is commonly used by sparse checkout and should not be cleared casually.
- Case-only renames, executable-bit changes, symlink handling, and line endings depend on config
  and filesystem behavior.
