# History-editing controls

Before rewriting, record:

```sh
git rev-parse <base> <tip>
git branch backup/<name>-before-rewrite <tip>
git log --graph --decorate --oneline <base>..<tip>
```

Build an explicit todo. Splitting normally marks a commit `edit`, resets its changes into the
worktree/index according to the plan, then creates atomic replacements. Review each staged diff.

Compare old and new series with `git range-diff` when appropriate and verify aggregate tree/content.
Rewriting invalidates commit signatures and can detach notes/tags or disrupt downstream branches.

For a published branch:

```sh
git fetch <remote> <branch>
git push <remote> <new-tip>:refs/heads/<branch>   --force-with-lease=refs/heads/<branch>:<exact-fetched-oid>
```

The exact syntax may be adapted to the runtime, but the lease must bind the verified ref and OID.
A rejection means stop, re-inspect, and re-plan—not widen the force.
