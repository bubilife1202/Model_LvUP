"""LvUP: Rubric-Anchored Adversarial Refinement (RAAR) loop.

Reference implementation of the inference-time loop evaluated in the paper
"Closing the Generation Gap: Rubric-Anchored Adversarial Refinement Lets an
Older Model Match Its Successor" (Park, 2026).

The loop wraps a single base model (all roles use the SAME weights) in five
role-separated, fresh-context stages:

  1. RUBRIC    — externalize binary success criteria before any generation
  2. GENERATE  — K diverse candidates under distinct strategy directives
  3. VERIFY    — adversarial, evidence-quoting defect hunt per candidate
  4. FUSE      — compose one answer from verified strengths, fixing defects
  5. GATE      — burden-of-proof-flipped exit: loop exits only when a fresh
                 adversarial verifier FAILS to find a FATAL/MAJOR defect;
                 otherwise the defect report drives a fresh-context revision

Usage:
    Set provider credentials in your environment, then run:
    python lvup.py --model claude-opus-4-8 --task task.txt

Every stage is a separate stateless API call: no stage ever sees the chain of
thought that produced the artifact it is judging. This is the load-bearing
design decision; see Section 4 of the paper.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import sys

import anthropic

K_CANDIDATES = 3
MAX_REVISIONS = 2
MAX_TOKENS = 8192

DIRECTIVES = [
    "Decompose the task into sub-requirements and edge cases first; handle "
    "every one explicitly before finalizing.",
    "First enumerate the ways typical answers to this kind of task go wrong; "
    "then write yours to avoid each failure.",
    "Produce the cleanest, most careful expert solution you can, then "
    "re-verify it line by line before finalizing.",
]

RUBRIC_PROMPT = """\
You are a rigorous evaluator preparing to grade answers to the task below.
Do NOT solve the task. Produce a success rubric: 8-12 binary (pass/fail)
criteria that a perfect answer must satisfy, covering the correctness
requirements, the task's exact output-format requirements, and the most
likely failure modes for this kind of task. Be concrete and mechanically
checkable.

=== TASK ===
{task}"""

GENERATE_PROMPT = """\
You are completing a task. Produce your answer directly, with no commentary
beyond what the task asks for.

=== TASK ===
{task}

=== APPROACH DIRECTIVE ===
{directive}

=== SUCCESS RUBRIC (your answer will be graded against this) ===
{rubric}"""

VERIFY_PROMPT = """\
You are an adversarial verifier. The answer below was written by someone
else and likely contains defects; your job is to find them. Verify by
careful reading and independent recomputation.

=== TASK ===
{task}

=== SUCCESS RUBRIC ===
{rubric}

=== ANSWER UNDER REVIEW ===
{answer}

=== INSTRUCTIONS ===
1. Check the answer against EVERY rubric criterion, one by one, quoting
   specific evidence from the answer.
2. For any computation (arithmetic, counting, algorithm logic, test-case
   behavior), independently recompute or trace it rather than trusting the
   answer. For code, mentally execute it against the trickiest edge cases
   the spec implies, including boundary values.
3. Report every defect as: [FATAL|MAJOR|MINOR] <where> - <what is wrong> -
   <evidence>. FATAL = wrong results or spec violation; MAJOR = likely
   wrong, missing requirement, or required-format violation; MINOR =
   stylistic.
4. You MUST actively hunt for defects; a verifier that rubber-stamps is
   worthless. Only after completing the full per-criterion check with
   evidence may you conclude.
5. End with exactly one line: VERDICT: PASS (zero FATAL/MAJOR defects) or
   VERDICT: FAIL."""

FUSE_PROMPT = """\
You are composing the final answer to a task. You are given {k} candidate
answers and an adversarial defect report for each.

=== TASK ===
{task}

=== SUCCESS RUBRIC ===
{rubric}

{candidates}

=== INSTRUCTIONS ===
Start from the strongest candidate, graft any superior parts from the
others, and fix EVERY genuine defect flagged in the reports (re-verify each
flagged defect yourself; if a report claim is itself mistaken, keep the
correct content). Your final message must be ONLY the finished deliverable
in exactly the format the task requires - no commentary."""

REVISE_PROMPT = """\
Your previously submitted answer to the task below was rejected by an
adversarial verifier. Fix every genuine defect it found (re-verify each
claim yourself; if the verifier is itself mistaken on a point, keep the
correct content).

=== TASK ===
{task}

=== SUCCESS RUBRIC ===
{rubric}

=== REJECTED ANSWER ===
{answer}

=== VERIFIER REPORT ===
{report}

Your final message must be ONLY the corrected deliverable in exactly the
format the task requires - no commentary."""


@dataclasses.dataclass
class LoopTrace:
    rubric: str = ""
    candidates: list = dataclasses.field(default_factory=list)
    reports: list = dataclasses.field(default_factory=list)
    gate_verdicts: list = dataclasses.field(default_factory=list)
    n_calls: int = 0
    answer: str = ""


class LvUP:
    def __init__(self, model: str, client: anthropic.Anthropic | None = None):
        self.model = model
        self.client = client or anthropic.Anthropic()

    def _call(self, prompt: str, trace: LoopTrace) -> str:
        trace.n_calls += 1
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    @staticmethod
    def _passed(report: str) -> bool:
        return re.search(r"VERDICT:\s*PASS", report[-300:], re.I) is not None

    def run(self, task: str) -> LoopTrace:
        t = LoopTrace()

        # 1. RUBRIC — fresh context, never sees any solution attempt
        t.rubric = self._call(RUBRIC_PROMPT.format(task=task), t)

        # 2. GENERATE — K diverse candidates, fresh contexts
        for d in DIRECTIVES[:K_CANDIDATES]:
            t.candidates.append(self._call(
                GENERATE_PROMPT.format(task=task, directive=d, rubric=t.rubric), t))

        # 3. VERIFY — adversarial defect hunt per candidate, fresh contexts
        for c in t.candidates:
            t.reports.append(self._call(
                VERIFY_PROMPT.format(task=task, rubric=t.rubric, answer=c), t))

        # 4. FUSE — compose from verified strengths
        cands = "\n\n".join(
            f"=== CANDIDATE {i+1} ===\n{c}\n\n--- DEFECT REPORT FOR "
            f"CANDIDATE {i+1} ---\n{r}"
            for i, (c, r) in enumerate(zip(t.candidates, t.reports)))
        t.answer = self._call(FUSE_PROMPT.format(
            k=len(t.candidates), task=task, rubric=t.rubric, candidates=cands), t)

        # 5. GATE — exit only on failure-to-refute
        for _ in range(MAX_REVISIONS):
            gate = self._call(VERIFY_PROMPT.format(
                task=task, rubric=t.rubric, answer=t.answer), t)
            if self._passed(gate):
                t.gate_verdicts.append("PASS")
                break
            t.gate_verdicts.append("FAIL")
            t.answer = self._call(REVISE_PROMPT.format(
                task=task, rubric=t.rubric, answer=t.answer, report=gate), t)

        return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--task", required=True, help="path to task prompt file")
    args = ap.parse_args()
    with open(args.task) as f:
        task = f.read()
    trace = LvUP(args.model).run(task)
    print(trace.answer)
    print(f"\n[lvup] calls={trace.n_calls} gates={trace.gate_verdicts}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
