import ollama


PLAN_SYSTEM_PROMPT = """You are a planning assistant. Given the user's intent, produce a short numbered plan.

OUTPUT FORMAT — follow this exactly:
## Plan
1. [First action — what to do and which tool to use, if any]
2. [Second action]
3. ...

RULES:
- Each step is ONE sentence describing an action.
- If a step needs a tool, name the tool. If no tool is needed, say "no tool needed".
- Do NOT include code, code blocks, or implementation details.
- Do NOT solve the problem. Only outline the steps.
- Maximum 10 steps."""


PLAN_REVIEWER_PROMPT = """You are reviewing a task plan. A good plan is a short numbered list of steps. Each step says what to do and which tool to use (if any).

FAIL ONLY if:
- The plan contains a full code implementation (multiple lines of actual code inside ``` blocks). Describing what the code will do in plain English is fine.
- The plan does not address what the user asked for.

PASS everything else. Be lenient. Err on the side of PASS.

Respond EXACTLY like this:

VERDICT: PASS
ISSUES:
- none

Or:

VERDICT: FAIL
ISSUES:
- (one sentence per issue)"""


def plan(intent: str) -> str:
    """Generate a step-by-step plan to fulfill the user's intent. Returns a numbered plan."""
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": intent},
        ],
    )
    return response.message.content


def plan_review(plan: str, intent: str) -> str:
    """Review a plan against the user's intent. Returns VERDICT: PASS or VERDICT: FAIL with issues."""
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {"role": "system", "content": PLAN_REVIEWER_PROMPT},
            {"role": "user", "content": f"## User Intent\n{intent}\n\n## Agent Plan\n{plan}"},
        ],
    )
    return response.message.content


TOOLS = [plan, plan_review]
