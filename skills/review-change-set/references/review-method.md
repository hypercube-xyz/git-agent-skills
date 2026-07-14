# Change-set review method

## Review the effective change

For branch review, establish the intended base and merge base. Inspect both the aggregate diff and
individual commits when commit structure matters.

A useful finding contains:

```text
[severity] path:line — concise defect
Condition: how the behavior is reached
Impact: what becomes incorrect or unsafe
Evidence: code/test/contract that supports the claim
Suggested direction: bounded remediation, not a speculative redesign
```

Do not inflate review volume. Prefer one root-cause finding over repeated symptoms.

Checks may create caches, generated files, lockfiles, or formatter output. Run them in a disposable
clone/container, or create a bounded temporary worktree and explicitly acknowledge shared Git
administrative metadata. Verify cleanup and the original target's HEAD, index, worktree, config,
and registrations afterward.
