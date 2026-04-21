def _tool_to_spec(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


async def list_tools(client, policy_tools=None) -> list[dict]:
    mcp_tools = await client.list_tools()
    tools = [_tool_to_spec(tool) for tool in mcp_tools]
    if policy_tools:
        tools.extend(policy_tools)
    return tools
