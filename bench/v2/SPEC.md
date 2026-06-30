# LvUP-Bench v2 — Construction Specification

Goal: a PUBLISHABLE, discriminative benchmark for measuring how inference-time
loops close the quality gap between cheaper/older LLMs and a frontier model.
v1 failed by saturation: 4/5 objective tasks were solved perfectly single-pass
by the base model. v2 therefore targets calibrated headroom at construction
time.

Post-collection audit note: the released v2 results show useful cheaper-tier
headroom but not full frontier-tier discrimination. Fable single-pass remains
near ceiling on most scored objective tasks. The paper therefore treats the
frontier-headroom target as a construction goal, reports the saturation
openly, and bases gap-closure claims only on the documented post-hoc
Fable-over-base headroom filter.

## Hard requirements (every task)

1. **Difficulty target**: a frontier model single-pass should score 0.3–0.85.
   Achieve this with MANY simultaneously-active rules/edge cases, exact-output
   requirements, and adversarial hidden cases — NOT with ambiguity or tricks.
   Each task ships a `difficulty_rationale` listing >=6 distinct failure traps.
   This target is not mechanically enforceable by `validate.py`; post-hoc model
   results must still be audited for saturation before making frontier-gap
   claims.
2. **Pure text completion**: solvable with no tools, no retrieval, no
   randomness in scoring. The model outputs one answer; a deterministic
   checker scores it in [0,1].
3. **Unambiguous spec**: the prompt must be authoritative and precise enough
   that two careful human experts would agree on correctness of any output.
   No reliance on unstated conventions.
4. **Novel content**: constructed for this benchmark; not copied from any
   known dataset/puzzle site. Template familiarity is acceptable; instance
   memorization must be impossible.
5. **Checker quality gates** (validation script must enforce):
   - The reference solution scores exactly 1.0.
   - At least one provided "near-miss" wrong solution is checked. For
     partial-credit tasks it must score in (0, 1.0), proving the checker has
     teeth and partial credit is meaningful. Exact-answer math tasks may set
     `near_miss_policy: "exact_zero_allowed"` and use a plausible wrong
     near-miss that scores exactly 0, because their scoring is intentionally
     all-or-nothing. Near-miss validation is a checker smoke test, not a claim
     that the numeric partial-credit scale is a semantic severity metric; some
     transform tasks use line- or case-level partial credit.
   - Code-task hidden tests: >=20 cases, plus a machine-readable
     `hidden_coverage` manifest with >=6 rule groups whose case references are
     validated against the shipped hidden cases. Hidden cases must be
     constructed so that plausible partial implementations fail specific cases.
   - Checkers are Python 3.9 stdlib-only, CLI: `python3 check.py <answer_file>`
     printing JSON `{"score": float, "detail": {...}}`.
6. **Math ground truths**: computed by TWO INDEPENDENT programs (different
   algorithms, e.g. pruned enumeration vs DP/analytic), asserted equal, both
   shipped. Enumeration must finish < 5 min on a laptop.
7. **English**, MIT-licensed, self-contained per-task directory.

## Directory layout (strict)

```
bench/v2/tasks/<task_id>/
  task.json          # {"id", "category", "verifiability": "high|medium|low",
                     #  "scoring": "...", "prompt": "...",
                     #  "difficulty_rationale": ["trap1", ...],
                     #  optional "near_miss_policy",
                     #  optional "hidden_coverage"}
  check.py           # CLI checker (for objective tasks)
  reference/         # reference solution / reference outputs / ground-truth
                     # programs (never shown to models)
  near_miss/         # >=1 plausible-but-flawed answer + expected score range
                     # in near_miss/expected.json: {"file.txt": [lo, hi], ...}
```

The model-facing prompt must instruct the exact output format the checker
parses (e.g. "output ONLY a single Python code block", or "end with
FINAL ANSWER: <integer>", or "output the transformed file verbatim, nothing
else").

## Verifiability tags (drives the paper's domain map)

- `high`: hidden tests / exact answers / mechanical constraint counts.
- `medium`: seeded-defect recall with keyword-signature auto-matching.
- `low`: open-ended judged tasks (no check.py; task.json only, plus
  `rubric_dims` field for judges).

## Validation runner

`bench/v2/validate.py` walks all tasks and enforces the machine-checkable gates:
reference scores, near-miss score ranges, hidden-case placement and coverage,
checker execution, and math ground-truth agreement. It prints a table with task,
ref score, near-miss scores, #hidden tests, and OK/FAIL, and exits nonzero on
any violation. Empirical difficulty, novelty, prompt ambiguity, and semantic
meaningfulness of partial-credit magnitudes require separate human/post-hoc
audit; they are not certified by the validator alone. The optional `--fast` flag
is accepted for CLI compatibility but currently performs the same full
validation; no cached or skipped checks are used. All validation must pass
without skipped tasks before the benchmark is used.
