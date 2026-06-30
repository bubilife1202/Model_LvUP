# Artifact Card

## Purpose

This artifact supports the claims in the Model_LvUP preprint by releasing the
benchmark tasks, checkers, scored outputs, statistics scripts, judge artifacts,
and paper source used for the reported LvUP-Bench v2 results.

## What Is Included

- `bench/v2/tasks/`: task prompts, references, checkers, and hidden tests where
  the task format supports them.
- `bench/v2/validate.py`: structural validator for task metadata, reference
  scores, near-miss behavior, hidden-test coverage, and math ground truth.
- `results/v2/all_runs.scored.json`: scored v2 run table used by the paper.
- `results/v2/stats.json`: generated summary statistics.
- `results/v2/judging/`: blinded pairwise judged comparisons and verdicts.
- `analysis/`: scripts used to regenerate statistics, domain maps, figures,
  and judge summaries.
- `paper/`: current source, PDF, and figure PDFs.

## What Is Not Included

- Private local workflow logs such as `.omo`, `.omc`, `.omx`, and `.claude`.
- Secrets, credentials, or provider API keys.
- Large historical transcript dumps and earlier exploratory runs that are not
  needed to reproduce the reported v2 paper numbers.
- A GPT-5.5 generator arm. GPT-5.5 is judge-only in this release.

## Reproducibility Commands

```bash
python3 bench/v2/validate.py
python3 analysis/v2_stats.py results/v2/all_runs.scored.json
python3 analysis/v2_domain_map.py results/v2/all_runs.scored.json
python3 analysis/v2_judging/aggregate_judgments.py results/v2/judging
```

Optional figure regeneration:

```bash
python3 -m pip install -r requirements.txt
python3 analysis/v2_figures.py results/v2/all_runs.scored.json
```

## Known Limitations

- The v2 benchmark is intentionally small and several headline estimates have
  tiny denominators.
- Some missing cells are failed no-answer collections; they are not interpreted
  as model-quality scores.
- Public judge file naming was normalized so the GPT-5.5 judge is not confused
  with a generation arm.
- The artifact is sufficient to inspect and recompute the reported tables, but
  not to rerun closed-model generations without separate provider access.
