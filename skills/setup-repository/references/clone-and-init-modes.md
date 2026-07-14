# Clone and initialization modes

## Choose by postcondition

- **Normal clone**: development checkout with full reachable history.
- **Bare clone**: repository without a working tree, commonly for server-side storage.
- **Mirror clone**: bare clone plus all refs and mirror fetch/push configuration; use for migration
  or exact replication, not ordinary development.
- **Shallow clone**: truncate commit ancestry; some history operations and pushes may be limited.
- **Partial clone**: retain history topology while deferring selected object content, usually blobs.
- **Single-branch clone**: narrow fetched branch refs; it is not the same as shallow history.
- **No-checkout clone**: obtain repository metadata without populating the worktree.

Sparse checkout is a worktree selection mechanism applied after or alongside clone strategy. It is
not a history truncation mechanism.

## Verify after setup

```sh
git rev-parse --show-toplevel
git remote -v
git status --porcelain=v2 --branch
git rev-parse --is-bare-repository
git rev-parse --is-shallow-repository
git config --get remote.origin.promisor
git config --get remote.origin.partialclonefilter
```

Never put passwords or tokens in a clone URL. Prefer credential helpers, SSH agents, or runtime
credential injection appropriate to the environment.
