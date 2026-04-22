def _tool_to_spec(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


async def list_tools(client, policy_tools=None, allowed_tool_names=None) -> list[dict]:
    mcp_tools = await client.list_tools()
    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        mcp_tools = [tool for tool in mcp_tools if tool.name in allowed]
    tools = [_tool_to_spec(tool) for tool in mcp_tools]
    if policy_tools:
        tools.extend(policy_tools)
    return tools
