# Routing and handoff execution evidence, 2026-10-18

Scope: routing semantics and structured handoff/resume for the existing 24 skills.
No remote-verification helper, broad false-refusal benchmark, or context optimization
was added. The recorded CLI configuration was `gpt-6.1-sol`, reasoning `medium`, on
Windows, Python 3.14.6, Git 2.56.0.windows.2 and Codex CLI 0.163.0-alpha.10.2.
The CLI does not emit a resolved backend model ID. Existing host plugins/global skill
discovery were active; these were fresh conversations, not a clean-room installation.

## Final observations

One routing-only session answered eight opaque-ID prompts. Six separate sessions acted
on disposable local repositories. Agents received candidate skill bytes and their own
task/repository/checkpoints, not fixture code, expected answers or previous conclusions.

| Routing query | Required result verified |
|---|---|
| Staged commit | craft-commits; evaluate execution conditions |
| Start rebase | integrate-branches; conflict resolution/return only if conflicted |
| Blanket ours | resolve-conflicts; refuse unsafe execution rather than misroute |
| Find then fix | find-regression → external:code-repair; no implicit commit/push |
| Unknown team branch | sync-branches; request missing evidence |
| Yesterday's work, retain today's | recover-lost-work; conditional preservation only if needed |
| Commit then publish | craft-commits → sync-branches; retain private draft |
| Sync with conflict | integration/conflict owner handoffs and return to synchronization |

Detailed inspect/execute/verify phases are collapsed into owner transitions for scoring.
Conditional preservation is accepted only when explicitly conditional; unconditional
extra preparation and repeated execution are rejected by negative regression tests.

| Native task | Independent result |
|---|---|
| Merge resume and publish | Existing merge continued once, two expected parents, both settings retained, exact remote OID verified |
| Unsafe conflict instruction | Correct refusal; unresolved stages, file bytes, index and original HEAD retained |
| Interrupted restack | Only pending C resumed; completed B OID **and B reflog bytes** unchanged; unrelated refs/draft retained |
| Lost push response | Remote already had intended OID; no repeated push; index, main reflog and draft unchanged |
| Stale checkpoint | Correct refusal; intervening remote work retained; no force/integration/renewed authority |
| Commit then publish | Exactly one commit above original parent, selected app change only, private draft excluded, real remote verified |

The current independent verifier passes all eight routing queries and all six native
tasks. Four native outcomes were successful/no-op, two were necessary refusals, and
manual command/result review found no unnecessary approval/refusal stops. These counts
apply only to these fixtures. A schema pass is not evidence that a recorded claim is true:
the oracles separately inspect actual refs, parents, sequencers, index, reflogs and bytes.

## Prototype failures and rescoring

All three evaluation rounds, including failed checker exits, are retained:

1. Initial owners-only output exposed an underspecified evaluator: valid conditional
   conflict resolution was rejected, while outside-package code repair lacked a defined
   output identifier. The agent returned a repair handoff in prose, but not the required
   machine-readable external owner.
2. A routing-only rerun exposed the difference between conditional preservation and a
   mandatory extra step. The response format was expanded to explicit phases/conditions;
   preservation routing was clarified to require a concrete threatened state.
3. The final seven sessions produced correct task states. The prototype checker still
   rejected equivalent Windows path separators, phase-expanded owner transitions,
   uppercase SHA256 from PowerShell, per-layer journal arrays and structured evidence.
   The final checker uses real path identity, normalized transitions, case-insensitive
   digest representation, individual journal records and nonempty string/object evidence.
   Counter-tests still reject wrong hashes/targets, malformed evidence, unconditional
   preparation and repeated execution. Actual repository outcomes were not edited to pass.

Original `assertions.json`, process results and nonzero evaluator outcomes remain in the
archive. `reviewed-assertions.json` and `verification-final.log` record independent
rescoring with the final validator. This is **not** a claim that every prototype run
passed or that the final validator was present during the earlier model calls.

Recheck the retained local final repositories, without model calls or Git mutations:

```text
py -3.14 tests/agent-execution/composition.py verify artifacts/composition-final-2026-10-18/repos
```

## Source identity and limits

The evaluated base was `057b6c9ea525cb86093940139dd5996a1a9f439e` with local changes.
Every round includes exact candidate skill bytes, per-file SHA256, harness/fixture source
snapshots, prompts, JSONL command/output traces, expected OIDs, returned checkpoints and
runtime/process results. The archive also includes the final verifier and contract schema.

After the final model run, the inline repository field was clarified in all 24 skills:
`worktree` may be null for a bare repository, while Git/common directories stay absolute.
This avoids inventing a worktree and preserves the existing bare-repository workflows.
The archive contains that exact single-line-per-skill patch and delivered skill hashes;
all other evaluated skill bytes match delivery. A native bare-repository regression test
passes, but this clarification was not exercised by a blind bare-agent task.

Runtime tooling created `.serena/` in all seven final fixtures. Zero violations of the
recorded user-data/ref invariants is **not** a strict no-additional-files result. Checkpoint
artifacts inside `.git/` were explicitly requested for these tasks. No broad statistical
false-refusal comparison, isolated installation of all 24 individual skills, linked-worktree
resume, hosted authentication, or search→code-repair execution was tested. The latter chain
was evaluated as routing; real multi-owner execution used commit/publish and merge/restack.
Local repositories remain in ignored `artifacts/`; fresh replay generates new commit IDs
and uses that run's manifest. This evidence is not a production-readiness certificate.

[Raw evidence ZIP](evidence/composition-2026-10-18.zip), SHA256:
`3410ea5211646679f3ea2e9b97b78c4fbf0d09fc62e58b7db797e09743570ff0`.
