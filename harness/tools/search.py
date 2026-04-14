import json
import urllib.request
import urllib.parse
from harness.config import load_config


def web_search(query: str) -> str:
    """Search the web using SearXNG and return the top results."""
    config = load_config()
    if not config.searxng_url:
        return "Error: searxng_url not set in harness.toml [services] section"

    url = f"{config.searxng_url.rstrip('/')}/search?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Error: search failed — {e}"

    results = data.get("results", [])
    if not results:
        return f"No results found for: {query}"

    lines = []
    for r in results[:10]:
        title = r.get("title", "")
        href = r.get("url", "")
        snippet = r.get("content", "")
        lines.append(f"**{title}**\n{href}\n{snippet}")

    return "\n\n".join(lines)


def fetch_url(url: str) -> str:
    """Fetch a URL and return the readable text content of the page."""
    from bs4 import BeautifulSoup

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Harness/0.1)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode(errors="replace")
    except Exception as e:
        return f"Error: failed to fetch {url} — {e}"

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean = "\n".join(lines)

    if len(clean) > 10_000:
        clean = clean[:10_000] + "\n\n[truncated]"

    return clean if clean else "Error: page returned no readable content"


TOOLS = [web_search, fetch_url]
