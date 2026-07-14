# Local branch lifecycle

Use full ref resolution when names can collide:

```sh
git rev-parse --verify <ref>^{commit}
git show-ref --verify refs/heads/<name>
git branch --show-current
git for-each-ref --format='%(refname) %(objectname) %(upstream) %(upstream:track)' refs/heads/
```

## Delete only with the intended base

`git branch -d` checks merge status relative to an upstream or HEAD, which may not be the base the
user means. For a material deletion, explicitly test ancestry against the intended retention ref:

```sh
git merge-base --is-ancestor refs/heads/<candidate> <retention-ref>
```

Also inspect commits unique to the candidate. Force deletion removes the ref, not the objects
immediately, but reflog expiry and garbage collection make that a temporary recovery story.

## Detached HEAD

If new commits exist, create a branch at the exact OID before switching away unless the user
explicitly chooses another preservation method. Do not claim detached state is itself corruption.
