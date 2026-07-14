# Submodule playbook

Inspect from the superproject:

```sh
git submodule status --recursive
# Compare the staged gitlink with HEAD.
git submodule summary --cached
# Compare the nested worktree with the index.
git submodule summary --files
git ls-files --stage -- <path>
git config -f .gitmodules --get-regexp '^submodule\.'
```

Mode `160000` in the index is the gitlink OID committed by the superproject. The nested checkout can
be dirty or at another commit without the superproject gitlink changing until staged.

Before removal, inventory nested refs, status, untracked files, and descendants. Before committing a
new gitlink, verify the nested commit exists in a destination collaborators can fetch; pushing the
superproject first can create a broken checkout.

Use `git submodule sync` after authoritative URL changes when local config should follow. Recursive
commands expand blast radius; enumerate descendants and apply only when they are all in scope.
