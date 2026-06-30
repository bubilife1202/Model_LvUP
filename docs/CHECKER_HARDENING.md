# Checker Hardening

## Scope

Hardened these four v2 code-task checkers so candidate code is evaluated from a fresh temp directory with only the extracted candidate module present:

- `bench/v2/tasks/cron_next/check.py`
- `bench/v2/tasks/interval_sched/check.py`
- `bench/v2/tasks/table_render/check.py`
- `bench/v2/tasks/tokenizer_debug/check.py`

Each checker now keeps hidden fixtures checker-side, runs the candidate with `cwd` set to the temp dir, and uses a scrubbed env that omits `PWD` and any task-dir path hints.

## Reference Solutions

Commands:

```bash
python3 bench/v2/tasks/cron_next/check.py bench/v2/tasks/cron_next/reference/answer.txt
python3 bench/v2/tasks/interval_sched/check.py bench/v2/tasks/interval_sched/reference/answer.md
python3 bench/v2/tasks/table_render/check.py bench/v2/tasks/table_render/reference/answer.md
python3 bench/v2/tasks/tokenizer_debug/check.py bench/v2/tasks/tokenizer_debug/reference/answer.md
```

Observed:

| task | score | detail |
| --- | ---: | --- |
| `cron_next` | `1.0` | `37 / 37` |
| `interval_sched` | `1.0` | `28 / 28` |
| `table_render` | `1.0` | `30 / 30` |
| `tokenizer_debug` | `1.0` | `26 / 26` |

## Cheat Scores

Before hardening, [`docs/ADVERSARIAL_REVIEW.md`](./ADVERSARIAL_REVIEW.md) recorded that simple fixture-reading cheats scored `1.0` on all four tasks.

After hardening, I re-ran equivalent cheats that attempt to read:

- `Path.cwd() / "bench/v2/tasks/.../reference/hidden_tests.json"`
- `Path(os.environ["PWD"]) / "bench/v2/tasks/.../reference/..."`

Commands:

```bash
python3 bench/v2/tasks/cron_next/check.py /private/tmp/model_lvup_hardening/cron_cheat_answer.md
python3 bench/v2/tasks/interval_sched/check.py /private/tmp/model_lvup_hardening/interval_cheat_answer.md
python3 bench/v2/tasks/table_render/check.py /private/tmp/model_lvup_hardening/table_cheat_answer.md
python3 bench/v2/tasks/tokenizer_debug/check.py /private/tmp/model_lvup_hardening/tokenizer_cheat_answer.md
```

Observed:

| task | before | after | failure mode |
| --- | ---: | ---: | --- |
| `cron_next` | `1.0` | `0.0` | import fails with `FileNotFoundError` |
| `interval_sched` | `1.0` | `0.0` | import fails with `FileNotFoundError` |
| `table_render` | `1.0` | `0.0` | import fails with `KeyError('PWD')` |
| `tokenizer_debug` | `1.0` | `0.0` | import fails with `FileNotFoundError` |

## Real Runs

Rescore command:

```bash
tmpdir=$(mktemp -d /private/tmp/model_lvup_score_cmp.XXXXXX)
cp results/v2/all_runs.json "$tmpdir/all_runs.json"
python3 analysis/score_v2.py "$tmpdir/all_runs.json" >/dev/null
```

Verification results:

- `215` scored rows had byte-identical `{task, arm, model, seed, score}` projections versus `results/v2/all_runs.scored.json`.
- `0` real submission `score` values moved.
- The full rescored JSON file is **not** byte-identical as a whole.

Why the full file still differs:

- `4` `interval_sched` rows include traceback strings in `score_detail.failures`.
- Those tracebacks embed the temp `candidate.py` path.
- The checked-in `results/v2/all_runs.scored.json` already contains earlier temp-path strings, so a fresh rescore regenerates different temp path text even though the numeric `score` fields stay identical.

This means the hardening preserves benchmark scores for real submissions, but `score_detail` remains path-nondeterministic for a small set of already-failing `interval_sched` runs.
