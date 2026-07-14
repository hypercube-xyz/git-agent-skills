# Branch synchronization playbook

## Classify after an authorized fetch

```sh
git rev-list --left-right --count <local>...<remote>
git merge-base <local> <remote>
git log --oneline --left-right <local>...<remote>
```

- **Equal**: no content movement required.
- **Local ahead only**: ordinary push may be valid after destination and policy checks.
- **Remote ahead only**: fast-forward local branch when the worktree is safe.
- **Diverged**: choose merge to preserve topology or rebase only when rewriting the local commits
  is permitted. Never select from global pull defaults without resolving intent.
- **Missing remote ref**: distinguish new branch, deleted branch, wrong fetch refspec, and stale
  tracking ref.

A push rejection is a concurrency/scope signal, not an instruction to force. Re-fetch, compare the
exact remote OID, and route any intentional non-fast-forward update to `edit-commit-history`.
