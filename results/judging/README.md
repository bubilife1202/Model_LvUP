# Study 1 Judging Artifacts

This directory contains the blinded pairwise judging artifacts for Study 1.

- `manifest.json` defines the 16 comparison prompts.
- `gpt55_judge_verdicts.jsonl`, `gemini_verdicts.jsonl`, and
  `claude_verdicts.json` are the primary verdict files used by
  `analysis/aggregate_judgments.py`.
- `gpt55_judge_verdicts_extra.jsonl` preserves a duplicate GPT-5.5 judge
  collection pass for auditability. Paper numbers use the first verdict per
  comparison and judge, reflected in `all_verdicts_deduped.json`.

The public GPT-5.5 judge filename normalizes the original internal collection
label. GPT-5.5 is used as a judge only, not as a generation arm.
