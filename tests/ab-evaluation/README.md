# Agent Routing Evaluation — git-agent-skills v1.2.1

Routing evaluation for the 24-skill package at commit
`30691f4d54c6b9a1632eb21b5f6aba7bd4d7aee6`.

The evaluation compares short taxonomy labels with full skill frontmatter
metadata. A true-baseline clear-case run is included as a ceiling check.

## Conditions

| Condition | Context |
|---|---|
| **true-baseline** | User prompt only; the free-form response is mapped to the package taxonomy after completion |
| **taxonomy-only** | User prompt, 24 skill names, and one-line catalog summaries |
| **full-metadata** | User prompt, 24 skill names, and full frontmatter descriptions |

No target label or target `SKILL.md` was preloaded.

## Clear-Case Sanity Gate

Ten clear routing prompts were used as a regression check. All conditions
reached the accuracy ceiling.

| Condition | Correct | Runs |
|---|---:|---:|
| true-baseline | 10/10 | 1 |
| taxonomy-only | 50/50 | 5 |
| full-metadata | 50/50 | 5 |

The clear-case suite is retained as a regression gate rather than a measure of
incremental metadata value.

## Near-Boundary Routing Pilot

Forty prompts covered ten high-overlap skill pairs. Each pair included
clear-left, clear-right, boundary, and underspecified prompts. One batched run
was performed per condition.

| Metric | Taxonomy-only | Full metadata | Delta |
|---|---:|---:|---:|
| Acceptable routes | 37/40 (92.5%) | 40/40 (100%) | +7.5 pp |
| Forbidden routes | 2 | 0 | -2 |
| Severity-weighted loss | 9 | 0 | -9 |

Full metadata corrected three clear misroutes:

- `NB02`: `craft-commits` → `undo-changes`
- `NB14`: `transplant-commits` → `integrate-branches`
- `NB25`: `transplant-commits` → `integrate-branches`

Three additional changes on underspecified prompts remained within the
acceptable route set.

## Verify Recorded Results

Requires Python 3.9 or newer. No third-party packages are required.

```bash
python3 score_results.py
```

The scorer recomputes the documented metrics from the recorded model responses
and frozen ground truth, verifies complete clear-case coverage, and checks the
stored result files. It verifies the recorded results; it does not rerun the
original model invocations.

To regenerate the near-boundary scored cache from the recorded responses:

```bash
python3 score_results.py --rewrite-nb-results
```

## Files

- `eval_data.json` — clear-case prompts and expected routes
- `clear_results.json` — clear-case observations
- `near_boundary_prompts.json` — near-boundary prompts and frozen ground truth
- `raw_responses.json` — raw near-boundary model responses
- `nb_results.json` — scored near-boundary observations
- `overlap_pairs.json` — all overlap signals and the selected test pairs
- `score_results.py` — deterministic scorer and result verifier
- `run_manifest.json` — source, model, runtime, and run metadata

## Limitations

- The near-boundary suite tested 10 of the 27 overlap signals.
- Each near-boundary condition was evaluated in one batched run.
- Decisions within a batch are not statistically independent.
- Prompt order was not randomized across repeated runs.
- Only one model and runtime were evaluated.
- Raw near-boundary responses are included; raw clear-case responses were not preserved.
- The evaluation measures routing, not end-to-end Git execution behavior.
- Results apply to the tested prompts and require replication before broader generalization.

Same license as the source repository.
