def serialize_tool_call(tool_call) -> dict:
    if isinstance(tool_call, dict):
        return tool_call
    function = getattr(tool_call, "function", None)
    if function is None:
        return {}
    return {
        "function": {
            "name": getattr(function, "name", ""),
            "arguments": dict(getattr(function, "arguments", {}) or {}),
        }
    }


def extract_tool_call(tool_call) -> tuple[str, dict]:
    if isinstance(tool_call, dict):
        function = tool_call.get("function", {})
        return function.get("name", ""), dict(function.get("arguments", {}) or {})
    function = getattr(tool_call, "function", None)
    if function is None:
        return "", {}
    return getattr(function, "name", ""), dict(getattr(function, "arguments", {}) or {})


def flatten_tool_result(result) -> str:
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))
