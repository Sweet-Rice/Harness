import ollama
from .logger import log_thinking


#determines extended thinking. decided each chat.
_thinking = False





async def get_tools(client):
    tools = await client.list_tools()
    ollama_tools = []
    for t in tools:
        ollama_tools.append({
            "type": "function",
            "function":{
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            }

        })
    return ollama_tools



async def loop(client, messages):
    ollama_tools = await get_tools(client)

    while True:
        response = ollama.chat(
            model="qwen3-coder",
            messages=messages,
            tools=ollama_tools,
            think= _thinking,
        )
        #print("DEBUG tool_calls:", response.message.tool_calls)
        #print("DEBUG content:", repr(response.message.content))

        print(f"DEBUG -- tools: {', '.join(tc.function.name for tc in response.message.tool_calls) if response.message.tool_calls else 'none'}")


        #Side channel - do NOT put in messages. 
        #We shall not pollute our context with logs

        if response.message.thinking:
            log_thinking(response.message.thinking)

        if response.message.tool_calls:
            messages.append(response.message)
            for tc in response.message.tool_calls:
                result = await client.call_tool(
                    tc.function.name,
                    tc.function.arguments,
                )
                print(f"TOOL -- {tc.function.name} returned: {result.data}")
                messages.append({"role": "tool", "content": str(result)})

                
            continue

        #Text response
        messages.append(response.message)
        print(response.message.content)
        break


def set_thinking(value: bool):
    global _thinking
    _thinking = value

