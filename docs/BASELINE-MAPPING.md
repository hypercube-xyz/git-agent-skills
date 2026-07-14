# Engineering Baseline Mapping

This document records how the package applies the supplied Engineering Baseline for SWE Agent
Skills. It is design traceability, not certification, and is not required at runtime.

| Baseline concern | Package implementation |
|---|---|
| Coherent problem class | Each skill owns one desired postcondition; adjacent outcomes route explicitly elsewhere. |
| Description as routing contract | Every frontmatter description includes capability, activation conditions, and near-miss boundaries. |
| Runtime independence | Material Git-specific evidence, decisions, action limits, stop conditions, and verification are in each package. |
| Progressive disclosure | `SKILL.md` contains the core operating contract; one focused direct reference holds conditional detail. |
| Evidence before assertion | Every skill names current-state evidence and distinguishes observation from inference/assumption. |
| Intent and protected state | Consequential skills define desired, incidental, protected, and prohibited effects. |
| No semantic escalation | Diagnosis does not repair; local work does not silently become network publication; normal push does not become force. |
| Consequence controls | Local mutation, external effects, destructive recovery, and critical migration/rewrite paths carry increasing controls. |
| Tool discipline | Exact refs/OIDs/paths and narrow commands are preferred; broad force, clean, prune, mirror, and wildcard actions are gated. |
| Partial failure | Every skill stops dependent work, inspects partial state, preserves evidence, and forbids a success claim. |
| Untrusted content | Repository text and tool output are data unless authority is independently established. |
| Data minimization | Secret scanning and remote inspection use redaction and avoid raw credential output. |
| Verification | Positive postconditions, protected state, incidental bounds, and prohibited effects are checked. |
| Package design | 25 focused skills, direct references, deterministic helper only where model redaction is insufficient, and test fixtures. |
| Validation | Structural validation, symptom-driven fixtures, semantic Git smoke tests, CLI discovery, and plugin validation are separated from future agent-runtime evaluation. |

## High-consequence examples

- `edit-commit-history` requires an explicit backup, exact rewrite range, publication analysis, and
  exact `--force-with-lease=<ref>:<oid>`.
- `migrate-repository` treats mirror deletion and cutover as critical external mutation with
  inventory, backup, approval, confirmation, staged verification, and rollback ownership.
- `scan-secrets` keeps values out of reports and routes credential rotation/history remediation to
  separately controlled workflows.
- `manage-tags` compares tag type, object, peeled target, annotation, and signature before declaring
  an existing tag idempotent.
