from .response import extract_tool_call, flatten_tool_result


async def dispatch_tool_call(client, tool_call, handlers=None, on_event=None) -> tuple[str, dict, str]:
    handlers = handlers or {}
    name, args = extract_tool_call(tool_call)
    if on_event:
        await on_event(
            "trace.tool_event",
            {
                "name": name,
                "status": "started",
                "args": args,
            },
        )

    try:
        if name in handlers:
            result_text = await handlers[name](client=client, args=args, on_event=on_event)
        else:
            result = await client.call_tool(name, args)
            result_text = flatten_tool_result(result)
        if on_event:
            await on_event(
                "trace.tool_event",
                {
                    "name": name,
                    "status": "completed",
                    "result_preview": result_text[:400],
                },
            )
    except Exception as exc:
        result_text = f"Error calling tool '{name}': {exc}"
        if on_event:
            await on_event(
                "trace.tool_event",
                {
                    "name": name,
                    "status": "failed",
                    "error": str(exc),
                },
            )
            await on_event("log", result_text)

    return name, args, result_text
