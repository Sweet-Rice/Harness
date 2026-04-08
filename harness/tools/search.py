import ollama
from duckduckgo_search import DDGS

MAX_SEARCH_RESULTS = 10
MAX_REFINEMENT_ROUNDS = 4

SEARCH_EVAL_PROMPT = """You are a search result evaluator. You are given:
1. The user's original INTENT (what they want to find/learn)
2. The SEARCH QUERY that was used
3. The SEARCH RESULTS (title, url, snippet for each result)

Your job: decide whether these results adequately address the user's intent.

If the results are GOOD ENOUGH to answer the user's intent:
Respond with:
VERDICT: PASS
SYNTHESIS:
(Write a comprehensive summary of the findings from the search results that addresses the user's intent. Cite URLs where relevant.)

If the results are NOT good enough (missing key information, too generic, off-topic):
Respond with:
VERDICT: FAIL
REASON: (one sentence explaining what's missing or wrong)
REFINED_QUERY: (a single improved search query using advanced techniques:
  - "exact phrase" for precise matching
  - site:example.com to target specific sites
  - intitle:keyword for title matches
  - filetype:pdf for specific file types
  - inurl:keyword for URL patterns
  - -exclude to remove irrelevant results
  - Combine multiple techniques as needed)

IMPORTANT: Do NOT use FAIL just because results could theoretically be better.
Use FAIL only when the results genuinely miss what the user needs."""


def _do_search(query: str) -> str:
    """Run a DuckDuckGo search and return formatted results string."""
    try:
        results = DDGS().text(query, max_results=MAX_SEARCH_RESULTS)
    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return "No results found."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] {r.get('title', 'No title')}\n"
            f"    URL: {r.get('href', 'No URL')}\n"
            f"    {r.get('body', 'No snippet')}"
        )
    return "\n\n".join(formatted)


def target_search(query: str, intent: str) -> str:
    """Iterative web search that refines queries using Google hacking techniques
    until results satisfy the intent. Returns synthesized findings."""

    current_query = query
    all_results_log = []

    for round_num in range(MAX_REFINEMENT_ROUNDS):
        results_text = _do_search(current_query)
        all_results_log.append(
            f"## Round {round_num + 1} — Query: {current_query}\n{results_text}"
        )

        eval_message = (
            f"## Intent\n{intent}\n\n"
            f"## Search Query\n{current_query}\n\n"
            f"## Search Results\n{results_text}"
        )

        response = ollama.chat(
            model="qwen3-coder",
            messages=[
                {"role": "system", "content": SEARCH_EVAL_PROMPT},
                {"role": "user", "content": eval_message},
            ],
        )
        eval_text = response.message.content

        if "VERDICT: PASS" in eval_text:
            if "SYNTHESIS:" in eval_text:
                return eval_text.split("SYNTHESIS:", 1)[1].strip()
            return eval_text

        if "REFINED_QUERY:" in eval_text:
            current_query = eval_text.split("REFINED_QUERY:", 1)[1].strip()
            current_query = current_query.split("\n")[0].strip()
        else:
            return (
                f"Search completed but could not refine further.\n\n"
                f"Last results:\n{results_text}"
            )

    # Max rounds exhausted — synthesize everything
    final_results = "\n\n---\n\n".join(all_results_log)
    response = ollama.chat(
        model="qwen3-coder",
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize the following search results to address the user's intent. "
                    "Be comprehensive and cite URLs."
                ),
            },
            {
                "role": "user",
                "content": f"## Intent\n{intent}\n\n## All Search Results\n{final_results}",
            },
        ],
    )
    return response.message.content


def deep_research(query: str, intent: str) -> str:
    """Deep research tool — architecture pending."""
    return "deep_research is not yet implemented — architecture pending."


TOOLS = [target_search, deep_research]
