# Study 1 Sanitized Public Transcripts

This directory contains sanitized, role-separated message transcripts for the
Study 1 local generation and verification runs used for the mechanism checks in
the paper.

The files are derived from the private local Study 1 transcript dump and retain
the ordered user/assistant message content needed to inspect the RAAR,
Self-Refine, best-of-3, single-pass, verifier, and judging behaviors. Opaque
local workflow metadata is intentionally removed: local filesystem paths,
working directories, session/request identifiers, timestamps, token accounting,
and hook/tool-list attachments are not part of the scientific artifact.

- `manifest.json` indexes 130 sanitized transcript files.
- Each `agent-*.jsonl` file begins with a metadata row, followed by ordered
  `message` rows with `role`, `content`, and, when present, `model`.
- The files are for auditability of qualitative mechanism claims. Scored
  quantitative claims should be recomputed from `results/all_objective.scored.json`
  and the scripts in `analysis/`.

Known scope: these transcripts support Study 1 mechanism inspection only. Study
2 quantitative claims are supported by the v2 run tables, validators, statistics
scripts, and judging artifacts under `results/v2/`.
