# Conflict semantics

Inspect the index stages:

```sh
git ls-files -u -- <path>
git show :1:<path>   # merge base
git show :2:<path>   # stage 2
git show :3:<path>   # stage 3
```

Stage labels are operation-dependent. During a normal merge, stage 2 is the current side and stage
3 is the merged side. During rebase, the checkout represents the rebased base and the replayed
commit is applied onto it, so user-facing “ours/theirs” intuition is often reversed.

## Decide from intent

Compare each side to the base. Preserve independent changes, choose one side only when the contract
makes the other obsolete, and reconstruct behavior when both edited the same abstraction.

Special cases:

- **modify/delete**: decide whether deletion remains intended after the modification.
- **rename/rename**: establish destination naming and update references.
- **binary**: choose/rebuild from authoritative source; markers cannot combine content.
- **submodule**: resolve the gitlink OID, not the nested worktree text.
- **generated files**: resolve source-of-truth inputs, then regenerate when policy requires.

`rerere` is a cache of prior conflict resolutions, not proof that a prior answer is correct now.
