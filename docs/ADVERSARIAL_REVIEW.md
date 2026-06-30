# Adversarial Review

This review tries to break the paper's central conditional claim by attacking four fronts: benchmark validity, comparison-arm fairness, statistics/cherry-picking, and missing controls. The review is evidence-backed and reproduction-first. I did not edit the paper or benchmark artifacts; I only wrote this report and [`results/v2/adversarial_review.json`](../results/v2/adversarial_review.json).

## Current Status

This is a historical adversarial review plus current-status notes. The first
finding, the code-task hidden-fixture leak, was valid at audit time but is
resolved in the current public artifact by the checker hardening documented in
[`CHECKER_HARDENING.md`](./CHECKER_HARDENING.md). The original `artifact_tmp/`
cheat files were local audit fixtures and are not release artifacts. The
remaining findings are retained as limitations, reviewer questions, or future
work rather than silently removed.

## Front 1: Benchmark Validity

### HISTORICAL FATAL, RESOLVED IN CURRENT ARTIFACT: the four code tasks were not truly hidden-test tasks

At audit time, the code-task checkers leaked their hidden fixtures to candidate
code. The candidate process could read the shipped hidden JSON and simply
return the expected outputs. This was not a corner case; four deliberately
broken lookup-table submissions from the local audit directory
`artifact_tmp/model_lvup_review/` each scored `1.0`.

Historical local evidence, retained for provenance. The `artifact_tmp/` files
were not part of the public release artifact and these commands are not public
rerun commands:

```bash
python3 bench/v2/tasks/cron_next/check.py artifact_tmp/model_lvup_review/cron_cheat_answer.md
python3 bench/v2/tasks/interval_sched/check.py artifact_tmp/model_lvup_review/interval_cheat_answer.md
python3 bench/v2/tasks/table_render/check.py artifact_tmp/model_lvup_review/table_cheat_answer_env.md
python3 bench/v2/tasks/tokenizer_debug/check.py artifact_tmp/model_lvup_review/tokenizer_cheat_answer.md
```

Observed:

- `cron_next`: `{"score": 1.0, "detail": {"passed": 37, "total": 37, ...}}`
- `interval_sched`: `{"score": 1.0, "detail": {"passed": 28, "total": 28, ...}}`
- `table_render`: `{"score": 1.0, "detail": {"passed": 30, "total": 30, ...}}`
- `tokenizer_debug`: `{"score": 1.0, "detail": {"passed": 26, "total": 26, ...}}`

The cheat files literally read:

```python
path = Path.cwd() / "bench/v2/tasks/cron_next/reference/hidden_tests.json"
...
base = Path(os.environ["PWD"]) / "bench/v2/tasks/table_render/reference"
```

Current public status: this finding is fixed in the released checker code. The
current checkers run candidate code from a fresh temp directory with scrubbed
path/env state, and the public structural validator passes.

Public rerun commands:

```bash
python3 bench/v2/validate.py
python3 bench/v2/tasks/cron_next/check.py bench/v2/tasks/cron_next/reference/answer.txt
python3 bench/v2/tasks/interval_sched/check.py bench/v2/tasks/interval_sched/reference/answer.md
python3 bench/v2/tasks/table_render/check.py bench/v2/tasks/table_render/reference/answer.md
python3 bench/v2/tasks/tokenizer_debug/check.py bench/v2/tasks/tokenizer_debug/reference/answer.md
```

The paper's current limitation text treats the original leak as a
load-bearing audit finding, states that no evaluated model exploited it, and
requires reuse with the hardening patch applied.

### MAJOR: `code_review_12` is regex stuffing, not objective review quality

The checker openly says it is approximate and non-semantic. A nonsense answer that repeatedly says “This is not a real defect” still scores full credit because it contains the seed keywords.

Evidence:

```bash
python3 bench/v2/tasks/code_review_12/check.py artifact_tmp/model_lvup_review/code_review_keyword_stuffing_v2.txt
sed -n '1,200p' artifact_tmp/model_lvup_review/code_review_keyword_stuffing_v2.txt
```

Observed:

- Score: `1.0`
- Matched seeds: all `S1..S12`

That means the task is not discriminating “find the real bugs” from “emit the seed vocabulary.”

### MAJOR: `constrained_writing_16` does not check the topic it claims to check

The prompt demands a single paragraph about a fictional weather station. The checker verifies only 16 mechanical constraints. An off-topic paragraph about bakers, runners, lanterns, platform 7, and theater still scores `16/16`.

Evidence:

```bash
python3 bench/v2/tasks/constrained_writing_16/check.py artifact_tmp/model_lvup_review/constrained_off_topic.txt
sed -n '1,200p' artifact_tmp/model_lvup_review/constrained_off_topic.txt
```

Observed:

- Score: `1.0`
- All constraints `C1..C16`: `true`

So the task is objectively scoring constraint satisfaction, not “weather-station writing.”

### MAJOR: several prompts are serialized with literal `\n` instead of real line breaks

This is a benchmark-authoring bug that leaks into evaluation. Some tasks are not presented as cleanly formatted prompts; they are presented as strings with escape sequences that the model must mentally decode.

Evidence:

```bash
python3 - <<'PY'
import json, pathlib
for path in sorted(pathlib.Path('bench/v2/tasks').glob('*/task.json')):
    obj=json.loads(path.read_text())
    p=obj['prompt']
    if '\\n' in p:
        print(obj['id'], 'literal_backslash_n', p.count('\\n'), 'actual_newline', p.count('\n'))
PY
```

Observed:

- `cron_next`: `literal_backslash_n 28`, `actual_newline 0`
- `perm_constraints`: `literal_backslash_n 14`, `actual_newline 0`
- `seq_runs`: `literal_backslash_n 7`, `actual_newline 0`
- `tokenizer_debug`: mixed literal and actual newlines
- `code_review_12`: mixed literal and actual newlines

At minimum, these tasks partly measure prompt-decoding robustness.

### MAJOR: output-format enforcement is inconsistent and often dominates semantics

Two bad patterns coexist:

- Semantically identical outputs can score `0.0` because formatting differs.
- Spec-violating outputs can still score `1.0` because extra text is ignored.

Evidence:

```bash
python3 bench/v2/tasks/records_merge/check.py artifact_tmp/records_compact.jsonl
python3 bench/v2/tasks/records_merge/check.py artifact_tmp/records_sorted.jsonl
python3 bench/v2/tasks/interval_sched/check.py artifact_tmp/interval_wrapped.md
python3 bench/v2/tasks/cron_next/check.py artifact_tmp/cron_wrapped.txt
```

Observed:

- Compact but semantically identical JSONL for `records_merge`: score `0.0`
- Sorted-key but semantically identical JSONL: score `0.25`
- `interval_sched` answer with preamble and postscript: score `1.0`
- `cron_next` answer with preamble and postscript: score `1.0`

So some tasks are really serialization tests, while others fail to enforce their own stated formatting rules.

### MINOR: one checker can crash instead of scoring

`constrained_writing_16/check.py` can throw `RuntimeError: generator raised StopIteration` on malformed no-alpha sentences instead of returning a score.

Evidence:

```bash
python3 bench/v2/tasks/constrained_writing_16/check.py artifact_tmp/model_lvup_review/constrained_no_alpha.txt
```

## Front 2: Comparison-Arm Fairness

### MAJOR: `base-direct` is a straw-man baseline

`base` is already a single-call direct-answer baseline. `base-direct` adds an extra instruction to answer immediately and not deliberate. The paper then uses the collapse from `0.730` to `0.478` as support that the scaffold is “load-bearing,” but that control is not neutral.

Evidence:

```bash
nl -ba harness/lvup_runner_v2.js | sed -n '34,36p'
python3 - <<'PY'
import json
from pathlib import Path
from collections import defaultdict
runs=json.loads(Path('results/v2/all_runs.scored.json').read_text())
per=defaultdict(lambda: defaultdict(list))
for r in runs:
    if r.get('model')=='sonnet' and r.get('arm') in {'base','base-direct','selfrefine','bo10','raar'} and 'score' in r:
        per[r['task']][r['arm']].append(r['score'])
common=[t for t,a in per.items() if all(k in a for k in ['base','base-direct','selfrefine','bo10','raar'])]
for arm in ['base','base-direct','selfrefine','bo10','raar']:
    vals=[sum(per[t][arm])/len(per[t][arm]) for t in common]
    print(arm, round(sum(vals)/len(vals),3))
PY
```

Observed common-11 means:

- `base`: `0.730`
- `base-direct`: `0.478`
- `selfrefine`: `0.901`
- `bo10`: `0.794`
- `raar`: `0.820`

### MAJOR: `bo10` is call-matched but not structure-matched

`bo10` is ten identical-prompt generations plus one selector. RAAR gets a generated rubric, directive-diversified candidates, adversarial reviews, fusion, and gate/revise. That means `bo10` is not a clean “same diverse generation, same compute, no verifier” control.

Evidence:

```bash
nl -ba harness/lvup_runner_v2.js | sed -n '72,111p'
python3 - <<'PY'
import json
from pathlib import Path
from collections import defaultdict
runs=json.loads(Path('results/v2/all_runs.scored.json').read_text())
by=defaultdict(set)
for r in runs:
    if 'score' in r:
        by[f"{r['arm']}@{r['model']}"].add(r.get('calls'))
for k in ['base@sonnet','base-direct@sonnet','selfrefine@sonnet','bo10@sonnet','raar@sonnet']:
    print(k, sorted(x for x in by[k] if x is not None))
PY
```

Observed call budgets:

- `base`: `1`
- `base-direct`: `1`
- `selfrefine`: `5`
- `bo10`: `11`
- `raar`: `9-12`

### MAJOR: RAAR gets privileged task decomposition and failure-mode hints

The rubric prompt explicitly asks for 8-12 binary criteria covering correctness, exact output-format requirements, and the most likely failure modes. Those criteria are then fed back into generation, verification, and fusion. Base never sees this decomposition.

Evidence:

```bash
nl -ba harness/lvup_runner_v2.js | sed -n '38,44p'
nl -ba harness/lvup_runner_v2.js | sed -n '82,100p'
```

This is not just “more calls.” It is extra task-specific scaffolding information.

### MAJOR: judged-task comparisons are completion-conditioned and silently truncated

The judged pipeline includes only runs with `answer is not None` and pairs sides with `zip`. Failed generations disappear, and extra completed generations on one side are silently dropped.

Evidence:

```bash
nl -ba analysis/v2_judging/gen_comparisons.py | sed -n '59,114p'
python3 - <<'PY'
import json
from pathlib import Path
runs=json.loads(Path('results/v2/all_runs.scored.json').read_text())
for r in runs:
    if r.get('excluded') and r['task'] in {'design_pipeline','explain_raft','migration_plan'}:
        print(r['task'], r['arm'], r['model'], r['seed'], r.get('calls'), r['excluded'])
manifest=json.loads(Path('results/v2/judging/manifest.json').read_text())
for m in manifest:
    if m['task']=='design_pipeline' and m['pair']==['raar@sonnet','base@sonnet']:
        print(m)
PY
```

This means the judged tail measures “who wins when both sides completed,” not end-to-end arm performance.

## Front 3: Statistics and Cherry-Picking

### FATAL: the 0.733 headline is threshold-sensitive post-hoc slicing

The `>0.05` Fable-over-Sonnet filter removes exactly one negative task, `code_review_12`, because its denominator is `0.041667`. Once that task is removed, the mean jumps from `0.500` to `0.733`.

Evidence:

```bash
python3 - <<'PY'
import json
from collections import defaultdict
runs=json.load(open('results/v2/all_runs.scored.json'))
cell=defaultdict(list)
for r in runs:
    if isinstance(r.get('score'), (int,float)) and not isinstance(r.get('score'), bool):
        cell[(r['task'], f"{r['arm']}@{r['model']}")].append(float(r['score']))
means={k: sum(v)/len(v) for k,v in cell.items()}
common=[]
for task in sorted({t for t,_ in means}):
    need=['base@sonnet','raar@sonnet','base@fable']
    if all((task,k) in means for k in need):
        denom=means[(task,'base@fable')]-means[(task,'base@sonnet')]
        num=means[(task,'raar@sonnet')]-means[(task,'base@sonnet')]
        common.append((task,denom,num))
for thr in [0.0,0.02,0.05,0.10]:
    vals=[num/den for _,den,num in common if den>thr]
    tasks=[t for t,den,_ in common if den>thr]
    print('threshold',thr,'n',len(vals),'mean',sum(vals)/len(vals) if vals else None,'tasks',tasks)
num=sum(num for _,den,num in common)
den=sum(den for _,den,num in common)
print('pooled_closure', num/den)
PY
```

Observed:

- Threshold `0.0`: mean `0.500`
- Threshold `0.02`: mean `0.500`
- Threshold `0.05`: mean `0.733`
- Threshold `0.10`: mean `0.667`
- Pooled macro closure across all 10 common scored tasks: `0.419`

The headline is therefore not robust to a very small threshold change.

### MAJOR: the ratio estimate is numerically unstable

The filtered estimate uses only five tasks. One per-task closure exceeds complete closure (`interval_sched = 1.1667`), and the reported 95% CI is `[0.300, 1.067]`, which already overshoots 100%.

Evidence:

```bash
python3 - <<'PY'
import json,random
stats=json.load(open('results/v2/stats.json'))
print('filtered_vals', [stats['gap_closure']['sonnet']['per_task'][t]['value'] for t in sorted(stats['gap_closure']['sonnet']['per_task'])])
print('reported_ci', stats['gap_closure']['sonnet']['overall']['ci95'])
PY
```

At threshold `0.0` or `0.02`, the CI widens further and includes negative improvement.

### MAJOR: duplicate and scoreless rows are silently excluded from the summaries

`all_runs.scored.json` contains duplicate `(task, arm, model, seed)` keys, including mixtures of no-answer and scored rows. `analysis/v2_stats.py` builds means from numeric scores only, so collection failures disappear from the aggregate view.

Evidence:

```bash
python3 - <<'PY'
import json
from collections import Counter,defaultdict
runs=json.load(open('results/v2/all_runs.scored.json'))
ctr=Counter((r['task'],r['arm'],r['model'],r.get('seed')) for r in runs)
for k,v in sorted((k,v) for k,v in ctr.items() if v>1):
    print(v,k)
rows=defaultdict(list)
for r in runs:
    rows[(r['task'],r['arm'],r['model'],r.get('seed'))].append(r)
for key,items in sorted(rows.items()):
    if len(items)>1:
        print('KEY',key)
        for it in items:
            print(' ',it.get('answer') is None,it.get('score'),it.get('excluded'),it.get('calls'))
PY
```

## Front 4: Missing Controls

### FATAL: there is no completed equal-scaffolding frontier control

The central practical claim is being sold as “one tier down plus RAAR approaches frontier quality,” but the frontier comparison is mostly Sonnet+RAAR versus Fable base. `raar@fable` is sparse and incomplete.

Evidence:

```bash
python3 - <<'PY'
import json
stats=json.load(open('results/v2/stats.json'))
for key in ['base@fable','raar@fable','base@sonnet','raar@sonnet']:
    row=stats['macro'][key]
    print(key,row['mean'],row['n_tasks'])
PY
```

Observed:

- `base@fable`: `10` task means
- `raar@fable`: `5` task means

That blocks a fair scaffold-vs-scaffold frontier claim.

### MAJOR: the paper lacks factorized component controls

There is no verifier-only arm, rubric-only arm, or `bo10-with-verifier` arm. The paper itself admits fully completed component ablations remain future work.

### MAJOR: the key results lack deep replication and human evaluation

- `base-direct@sonnet` has only one seed.
- Many Sonnet ablations have one or two seeds per task.
- The judged tail has only 56 total verdicts and no human evaluation.

Evidence:

```bash
python3 analysis/v2_judging/aggregate_judgments.py results/v2/judging
```

## Checks Run

Repository-standard structural validation:

```bash
python3 bench/v2/validate.py
```

This passed. That result is not exculpatory; it only shows the artifact passes its own structural gates.

Additional adversarial re-runs:

```bash
python3 bench/v2/tasks/code_review_12/check.py artifact_tmp/model_lvup_review/code_review_keyword_stuffing_v2.txt
python3 bench/v2/tasks/constrained_writing_16/check.py artifact_tmp/model_lvup_review/constrained_off_topic.txt
python3 bench/v2/tasks/constrained_writing_16/check.py artifact_tmp/model_lvup_review/constrained_no_alpha.txt
python3 bench/v2/tasks/records_merge/check.py artifact_tmp/records_compact.jsonl
python3 bench/v2/tasks/records_merge/check.py artifact_tmp/records_sorted.jsonl
python3 bench/v2/tasks/interval_sched/check.py artifact_tmp/interval_wrapped.md
python3 bench/v2/tasks/cron_next/check.py artifact_tmp/cron_wrapped.txt
```

## Bottom Line

The original audit found that the benchmark was not just noisy: parts of it
were invalid for the stronger claims then being made. In the current public
artifact, the hidden-fixture leak is resolved by checker hardening, while the
other issues remain important limitations: one “objective” review task can be
keyword-gamed to perfect score, one writing task ignores its own topic
semantics, the strongest Sonnet headline depends on excluding a single negative
task just below a post-hoc threshold, and the frontier comparison is not
equal-scaffolding. The paper should therefore be read as a narrow within-family
descriptive result with explicit limitations, not as a broad claim of frontier
parity.
