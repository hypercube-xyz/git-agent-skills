# Recovery playbook

Search from least invasive and most contextual to broadest:

```sh
git reflog show --all --date=iso
git reflog show HEAD
git reflog show refs/stash
git fsck --no-reflogs --unreachable
```

Also inspect operation-specific anchors such as `ORIG_HEAD`, rebase backup refs, and branch reflogs.
Do not expire reflogs or run pruning while recovery is open.

For each commit candidate:

```sh
git show --stat --summary <oid>
git diff <oid>^ <oid>
git ls-tree -r <oid>
```

Create a new recovery name before changing current state:

```sh
git branch recovery/<descriptive-name> <exact-oid>
```

Untracked files that were overwritten or deleted may never have entered Git's object database.
Filesystem backups, editor history, CI artifacts, or remote copies may be the only sources.
