# Repository migration runbook

Inventory refs without relying only on branch/tag lists:

```sh
git for-each-ref --format='%(refname) %(objectname)'
git show-ref --head
git lfs ls-files --all
git submodule status --recursive
```

Classify refs: branches, tags, notes, pull-request/provider refs, backup refs, replace refs, and
temporary namespaces. Decide which are authoritative and whether the destination supports them.

`git push --mirror` makes destination refs match the source and can delete refs. Use only after a
complete destination dry-run/inventory, explicit approval, backup, and exact destination
verification. An explicit refspec set is safer when the scope is narrower.

Git transfer does not automatically migrate issues, reviews, releases, repository settings,
permissions, secrets, actions, webhooks, wikis, or LFS objects. Track each data class with its own
method, acceptance check, owner, and rollback response.
