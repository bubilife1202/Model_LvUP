export const meta = {
  name: 'lvup-runner-v2',
  description: 'LvUP v2 arm runner: model matrix (haiku/sonnet/opus/fable) x arms (base, base-direct, selfrefine, boN, raar, raar-norubric, raar-approval)',
  phases: [{ title: 'Load' }, { title: 'Run' }],
}

// args: { taskIds: [...], runs?: [{taskId, arm, model, seed}],
//         model?, matrixTaskIds?, matrix?: {arm: [seeds]},
//         matrix2TaskIds?, matrix2?: {arm: [seeds]} }
const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const TASK_IDS = ARGS.taskIds
const RUNS = ARGS.runs || []
for (const [ids, mat] of [[ARGS.matrixTaskIds, ARGS.matrix], [ARGS.matrix2TaskIds, ARGS.matrix2]]) {
  if (ids && mat) for (const t of ids) for (const arm of Object.keys(mat))
    for (const s of mat[arm]) RUNS.push({ taskId: t, arm, model: ARGS.model, seed: s })
}

phase('Load')
const LOAD_SCHEMA = {
  type: 'object',
  properties: { tasks: { type: 'array', items: {
    type: 'object',
    properties: { id: { type: 'string' }, prompt: { type: 'string' } },
    required: ['id', 'prompt'] } } },
  required: ['tasks'],
}
const taskFiles = TASK_IDS.map(t => `bench/v2/tasks/${t}/task.json`)
const loaded = await agent(
  `Use the Read tool to read these files, one per task id: ${taskFiles.join(' , ')} . From each, extract the exact, verbatim value of the "prompt" field (preserve every character, including newlines). Return via StructuredOutput: {tasks: [{id, prompt}, ...]} for all ${TASK_IDS.length} tasks. Do not read any other files.`,
  { label: 'load-tasks', phase: 'Load', model: 'sonnet', schema: LOAD_SCHEMA })
const PROMPTS = {}
for (const t of loaded.tasks) PROMPTS[t.id] = t.prompt
for (const id of TASK_IDS) if (!PROMPTS[id]) throw new Error('missing prompt for ' + id)

const WRAP = (p, runId) => `You are completing a benchmark task (run ${runId}). IMPORTANT: do not use any tools; produce your answer directly as text in your final message, with no commentary beyond what the task asks for.\n\n=== TASK ===\n${p}`

const DIRECT_WRAP = (p, runId) => `You are completing a benchmark task (run ${runId}). IMPORTANT: do not use any tools. Answer immediately and directly with your best final answer; do not produce lengthy deliberation. Your final message must contain only what the task asks for.\n\n=== TASK ===\n${p}`

const VERIFY = (p, rubric, ans) => `You are an adversarial verifier. The answer below was written by someone else and likely contains defects; your job is to find them. Do not use any tools — verify by careful reading and independent recomputation.\n\n=== TASK ===\n${p}\n\n${rubric ? `=== SUCCESS RUBRIC ===\n${rubric}\n\n` : ''}=== ANSWER UNDER REVIEW ===\n${ans}\n\n=== INSTRUCTIONS ===\n1. Check the answer against ${rubric ? 'EVERY rubric criterion' : 'EVERY explicit requirement of the task'}, one by one, quoting specific evidence from the answer.\n2. For any computation (arithmetic, counting, algorithm logic, test-case behavior), independently recompute or trace it rather than trusting the answer. For code, mentally execute it against the trickiest edge cases the spec implies, including boundary values.\n3. Report every defect as: [FATAL|MAJOR|MINOR] <where> — <what is wrong> — <evidence>. FATAL = wrong results or spec violation; MAJOR = likely wrong, missing requirement, or required-format violation; MINOR = stylistic.\n4. You MUST actively hunt for defects; a verifier that rubber-stamps is worthless. Only after completing the full check with evidence may you conclude.\n5. End with exactly one line: VERDICT: PASS (zero FATAL/MAJOR defects) or VERDICT: FAIL.`

const APPROVAL_REVIEW = (p, rubric, ans) => `You are reviewing an answer to a task before it is submitted. Do not use any tools.\n\n=== TASK ===\n${p}\n\n${rubric ? `=== SUCCESS RUBRIC ===\n${rubric}\n\n` : ''}=== ANSWER ===\n${ans}\n\n=== INSTRUCTIONS ===\nReview the answer against the task${rubric ? ' and rubric' : ''}. If it is satisfactory, end with exactly: VERDICT: PASS. If it has problems, briefly list them and end with exactly: VERDICT: FAIL.`

const FUSE = (p, rubric, cands, reports) => `You are composing the final answer to a task. You are given ${cands.length} candidate answers and an adversarial defect report for each.\n\n=== TASK ===\n${p}\n\n${rubric ? `=== SUCCESS RUBRIC ===\n${rubric}\n\n` : ''}${cands.map((c, i) => `=== CANDIDATE ${i + 1} ===\n${c}\n\n--- DEFECT REPORT FOR CANDIDATE ${i + 1} ---\n${reports[i]}`).join('\n\n')}\n\n=== INSTRUCTIONS ===\nStart from the strongest candidate, graft any superior parts from the others, and fix EVERY genuine defect flagged in the reports (re-verify each flagged defect yourself; if a report claim is itself mistaken, keep the correct content). Do not use any tools. Your final message must be ONLY the finished deliverable in exactly the format the task requires — no commentary.`

const REVISE = (p, rubric, ans, gate) => `Your previously submitted answer to the task below was rejected by a reviewer. Fix every genuine defect it found (re-verify each claim yourself; if the reviewer is itself mistaken on a point, keep the correct content). Do not use any tools.\n\n=== TASK ===\n${p}\n\n${rubric ? `=== SUCCESS RUBRIC ===\n${rubric}\n\n` : ''}=== REJECTED ANSWER ===\n${ans}\n\n=== REVIEWER REPORT ===\n${gate}\n\nYour final message must be ONLY the corrected deliverable in exactly the format the task requires — no commentary.`

const DIRECTIVES = [
  'Decompose the task into sub-requirements and edge cases first; handle every one explicitly before finalizing.',
  'First enumerate the ways typical answers to this kind of task go wrong; then write yours to avoid each failure.',
  'Produce the cleanest, most careful expert solution you can, then re-verify it line by line before finalizing.',
]

const L = (t, a, m, s, stage) => ({ label: `${t}:${a}:${m}:s${s}:${stage}`, phase: 'Run', model: m })

async function baseArm(p, t, m, seed, direct) {
  const w = direct ? DIRECT_WRAP(p, `${t}-s${seed}`) : WRAP(p, `${t}-s${seed}`)
  const a = await agent(w, L(t, direct ? 'based' : 'base', m, seed, 'gen'))
  return { answer: a, calls: 1 }
}

async function selfRefine(p, t, m, seed) {
  let ans = await agent(WRAP(p, `${t}-sr-s${seed}`), L(t, 'sr', m, seed, 'draft'))
  let calls = 1
  for (let r = 0; r < 2; r++) {
    const fb = await agent(`${WRAP(p, `${t}-sr-s${seed}`)}\n\n=== YOUR PREVIOUS ANSWER ===\n${ans}\n\n=== INSTRUCTION ===\nThis is your own previous answer. Critique it carefully: look for errors, omissions, spec violations, and formatting problems. Output your critique as actionable feedback. Do not rewrite the answer yet.`, L(t, 'sr', m, seed, `fb${r}`))
    calls++
    ans = await agent(`${WRAP(p, `${t}-sr-s${seed}`)}\n\n=== YOUR PREVIOUS ANSWER ===\n${ans}\n\n=== YOUR CRITIQUE OF IT ===\n${fb}\n\n=== INSTRUCTION ===\nApply the critique and output an improved answer. Your final message must be ONLY the improved deliverable in exactly the format the task requires.`, L(t, 'sr', m, seed, `rev${r}`))
    calls++
  }
  return { answer: ans, calls }
}

async function boN(p, t, m, seed, n) {
  const cands = (await parallel(Array.from({ length: n }, (_, i) => () =>
    agent(WRAP(p, `${t}-bo${n}-s${seed}.${i}`), L(t, `bo${n}`, m, seed, `g${i}`))
  ))).filter(Boolean)
  const sel = await agent(`You are judging candidate answers to a task. Do not use any tools.\n\n=== TASK ===\n${p}\n\n${cands.map((c, i) => `=== CANDIDATE ${i + 1} ===\n${c}`).join('\n\n')}\n\nCompare the candidates for correctness and compliance with the task. End your message with exactly one line: BEST: <number>`, L(t, `bo${n}`, m, seed, 'sel'))
  const mm = sel.match(/BEST:\s*(\d+)/i)
  const idx = mm ? Math.min(Math.max(parseInt(mm[1], 10) - 1, 0), cands.length - 1) : 0
  return { answer: cands[idx], calls: cands.length + 1, picked: idx + 1 }
}

async function raar(p, t, m, seed, opts) {
  const useRubric = !opts.norubric
  const reviewFn = opts.approval ? APPROVAL_REVIEW : VERIFY
  let calls = 0
  let rubric = null
  if (useRubric) {
    rubric = await agent(`You are a rigorous evaluator preparing to grade answers to the task below. Do NOT solve the task and do not use any tools. Produce a success rubric: 8-12 binary (pass/fail) criteria that a perfect answer must satisfy, covering the correctness requirements, the task's exact output-format requirements, and the most likely failure modes for this kind of task. Be concrete and mechanically checkable.\n\n=== TASK ===\n${p}`, L(t, opts.tag, m, seed, 'rubric'))
    calls++
  }
  const cands = (await parallel(DIRECTIVES.map((d, i) => () =>
    agent(`${WRAP(p, `${t}-${opts.tag}-s${seed}.${i}`)}\n\n=== APPROACH DIRECTIVE ===\n${d}${useRubric ? `\n\n=== SUCCESS RUBRIC (your answer will be graded against this) ===\n${rubric}` : ''}`, L(t, opts.tag, m, seed, `gen${i}`))
  ))).filter(Boolean)
  calls += cands.length
  const reports = await parallel(cands.map(c => () =>
    agent(reviewFn(p, rubric, c), L(t, opts.tag, m, seed, 'verify'))
  ))
  calls += reports.filter(Boolean).length
  let answer = await agent(FUSE(p, rubric, cands, reports.map(r => r || '(reviewer unavailable)')), L(t, opts.tag, m, seed, 'fuse'))
  calls++
  const verdicts = []
  for (let r = 0; r < 2; r++) {
    const gate = await agent(reviewFn(p, rubric, answer), L(t, opts.tag, m, seed, `gate${r}`))
    calls++
    const pass = /VERDICT:\s*PASS/i.test((gate || '').slice(-300))
    verdicts.push(pass ? 'PASS' : 'FAIL')
    if (pass) break
    answer = await agent(REVISE(p, rubric, answer, gate), L(t, opts.tag, m, seed, `revise${r}`))
    calls++
  }
  return { answer, calls, verdicts }
}

phase('Run')
log(`launching ${RUNS.length} arm-runs over ${TASK_IDS.length} tasks`)

const results = await parallel(RUNS.map(({ taskId, arm, model, seed }) => async () => {
  const p = PROMPTS[taskId]
  let r
  if (arm === 'base') r = await baseArm(p, taskId, model, seed, false)
  else if (arm === 'base-direct') r = await baseArm(p, taskId, model, seed, true)
  else if (arm === 'selfrefine') r = await selfRefine(p, taskId, model, seed)
  else if (arm.startsWith('bo')) r = await boN(p, taskId, model, seed, parseInt(arm.slice(2), 10))
  else if (arm === 'raar') r = await raar(p, taskId, model, seed, { tag: 'raar' })
  else if (arm === 'raar-norubric') r = await raar(p, taskId, model, seed, { tag: 'raarNR', norubric: true })
  else if (arm === 'raar-approval') r = await raar(p, taskId, model, seed, { tag: 'raarAP', approval: true })
  else throw new Error('unknown arm ' + arm)
  return { task: taskId, arm, model, seed, ...r }
}))

return results.filter(Boolean)
