# Large-file and LFS decisions

First identify whether the limit applies to a worktree file, Git blob, pack, push, or hosted LFS
object. File size in the current checkout does not by itself locate the offending historical blob.

Inspect:

```sh
git check-attr -a -- <path>
git lfs env
git lfs ls-files
git cat-file -s <object>
```

A valid LFS pointer contains a version line, an `oid sha256:...`, and a size. Verify the object hash
against retrieved content without printing binary data.

`git lfs track` changes `.gitattributes`; re-add selected files to create pointers for future
commits. `git lfs migrate` is a history rewrite and must use exact refs/path patterns, backups,
consumer analysis, and controlled publication. Prefer avoiding migration when a future-only policy
satisfies the goal.
