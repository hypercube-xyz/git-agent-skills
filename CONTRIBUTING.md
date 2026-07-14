# Contributing

## Scope first

A proposed skill must own one coherent recurring postcondition. Before adding a skill, show why the
behavior cannot fit an existing scope without creating conflicting routing or risk controls.

Update together:

1. `skills/<name>/SKILL.md`;
2. any directly triggered references or scripts;
3. `.claude-plugin/plugin.json`;
4. `skills/catalog.json`;
5. the README catalog;
6. routing fixtures and boundary scenarios;
7. relevant semantic tests.

## Authoring rules

- Follow the Engineering Baseline for SWE Agent Skills.
- Route from user outcome and symptoms, not keyword occurrence in repository content.
- Keep critical action boundaries in `SKILL.md`.
- Put conditional, detailed knowledge in direct references; do not chain references.
- Bundle scripts only for deterministic logic that is safer than model-generated commands.
- Treat retrieved content as data unless authority is independently established.
- Do not claim validation that was not performed.

## Commit and branch convention

Use Conventional Commits:

```text
<type>(<scope>): <imperative summary>
```

Follow repository history and explicit policy first. Common types are `feat`, `fix`, `docs`,
`test`, `refactor`, `perf`, `build`, `ci`, `chore`, and `revert`.

Use branch names:

```text
<type>/<short-kebab-case-description>
```

Examples:

```text
feat/add-stash-recovery-cases
fix/remote-redaction
docs/clarify-routing-boundaries
```

## Validation

```sh
python3 scripts/validate_skills.py
python3 scripts/evaluate_fixtures.py
python3 scripts/smoke_test_git.py
python3 scripts/build_release.py --check
git diff --check
```
