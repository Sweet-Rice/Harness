import ollama


OUTPUT_SYSTEM_PROMPT = """You are an execution assistant. You are given an approved plan and the user's original intent. Your job is to carry out the plan and produce the deliverable.

INSTRUCTIONS:
- Work through each step of the plan.
- For code generation tasks: write the complete, working code.
- For explanations or summaries: write the full text.
- Do NOT restate or summarize the plan. Produce ONLY the deliverable.
- Your response should contain the final result the user asked for, nothing else."""


OUTPUT_REVIEWER_PROMPT = """You are reviewing an AI agent's output. The user's original request is the source of truth.

Check:
1. Does the output satisfy what the user originally asked for? This is the most important check.
2. If code was produced, does it have bugs that would cause runtime errors or wrong output?
3. Did the agent follow any constraints the user specified (e.g. "do not write files", "use Python", etc.)?

FAIL if the output does not fulfill the user's request or violates their constraints.
PASS if the user would be satisfied with this output.

Respond EXACTLY like this:

VERDICT: PASS
ISSUES:
- none

Or:

VERDICT: FAIL
ISSUES:
- (one sentence per issue)"""


def output(plan: str, intent: str) -> str:
    """Execute an approved plan and produce the deliverable. Returns the final output."""
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": OUTPUT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"## User Intent\n{intent}\n\n## Approved Plan\n{plan}",
            },
        ],
    )
    return response.message.content


def output_review(output: str, plan: str, intent: str) -> str:
    """Review output against the plan and user intent. Returns VERDICT: PASS or VERDICT: FAIL with issues."""
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": OUTPUT_REVIEWER_PROMPT},
            {
                "role": "user",
                "content": f"## User Intent\n{intent}\n\n## Approved Plan\n{plan}\n\n## Agent Output\n{output}",
            },
        ],
    )
    return response.message.content


TOOLS = [output, output_review]
