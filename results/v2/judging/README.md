# Judging Artifacts

This directory contains the blinded pairwise judging artifacts used by the
paper's judged-tail analysis.

- `manifest.json`: comparison metadata.
- `cmp*.txt`: blinded comparison prompts.
- `gpt55_judge_verdicts.jsonl`: GPT-5.5 judge verdicts.
- `gemini_verdicts.jsonl`: Gemini judge verdicts.

The local research workspace originally stored GPT-5.5 judge verdicts under an
internal interface-oriented filename. The public artifact normalizes that file
name and the `judge` field to `gpt55_judge` so readers do not confuse the judge
with a generator arm. No verdict outcomes or paper statistics were changed by
this normalization.
