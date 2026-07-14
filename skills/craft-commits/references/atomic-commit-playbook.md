# Atomic commit playbook

## Partition by reason

A useful unit answers one question: *why must these lines change together?* Keep implementation,
tests, fixtures, and narrowly required documentation together when they establish the same
behavior. Separate formatting, generated churn, dependency updates, unrelated cleanup, and
mechanical renames unless they are inseparable from the postcondition.

## Message convention precedence

1. Explicit current task.
2. Authoritative repository instructions or commit tooling.
3. Dominant recent history for comparable commits.
4. Conventional Commits fallback:

```text
<type>(<optional-scope>): <imperative summary>
```

Use `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, or `revert` according
to observable intent. Use `!` and a `BREAKING CHANGE:` footer only for an actual incompatible
contract change.

## Staging discipline

Prefer exact paths or interactive patch staging. Re-read:

```sh
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Do not use partial staging when a single file's hunks depend on each other in a way that makes an
intermediate commit invalid or misleading. After every commit, re-run status and verify that
protected local work remains outside the commit.
