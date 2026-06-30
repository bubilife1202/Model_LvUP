# Model_LvUP

This repository is the public reproducibility artifact for the preprint
**Inference-Time Scaffolding Across Two Axes: Closing a Cross-Generation Gap
and Climbing a Model-Tier Ladder with Rubric-Anchored Adversarial Refinement**.

The artifact contains the RAAR method, LvUP-Bench v2 tasks and checkers,
scored experiment outputs, analysis scripts, blinded judge artifacts, and the
current paper source/PDF.

## Current Paper

- PDF: `paper/main.pdf`
- LaTeX source: `paper/main.tex`

## Scope

The generator comparisons in this artifact are Claude-family comparisons:
Haiku, Sonnet, Opus, and Fable. GPT-5.5 is used as a blinded judge only.
There is no GPT-5.5 generation arm in `results/v2/all_runs.scored.json`.

The public judge file `results/v2/judging/gpt55_judge_verdicts.jsonl`
normalizes the internal collection label from the original local artifact to
make the judge role explicit. This rename does not change verdict contents or
paper numbers.

## Repository Layout

```text
analysis/                 scoring, statistics, figures, and judge aggregation
bench/v2/                 LvUP-Bench v2 task suite and validator
docs/                     checker hardening and domain-map notes
harness/                  RAAR reference implementation
paper/                    current paper source, PDF, and figures
results/v2/               raw/scored v2 runs, stats, reviews, and judge data
```

## Quick Verification

Run from the repository root:

```bash
python3 bench/v2/validate.py
python3 analysis/v2_stats.py results/v2/all_runs.scored.json
python3 analysis/v2_domain_map.py results/v2/all_runs.scored.json
python3 analysis/v2_judging/aggregate_judgments.py results/v2/judging
```

The core verification and statistics scripts use the Python standard library.
Figure regeneration uses Matplotlib, and the optional RAAR reference runner uses
the Anthropic SDK:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/v2_figures.py results/v2/all_runs.scored.json
```

## Main v2 Numbers

Macro means over scored task means:

| Arm | Macro |
|---|---:|
| Haiku base | 0.376 |
| Haiku+RAAR | 0.650 |
| Sonnet base | 0.721 |
| Sonnet+RAAR | 0.820 |
| Fable base | 0.972 |
| Fable+RAAR | 0.967 |

Important caveats:

- Sonnet+RAAR remains below Fable overall.
- The strongest Sonnet gap-closure claim is filtered to 5 common
  verification-shaped tasks with documented Fable-over-Sonnet headroom.
- Failed no-answer cells are reported as collection failures, not as
  model-quality scores.
- The equal-scaffolding frontier matrix is incomplete.

## Citation

Use `CITATION.cff` for the artifact citation. If citing the paper, cite the
arXiv version once available.
