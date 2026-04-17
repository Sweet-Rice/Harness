import os
import ollama 



from dotenv import load_dotenv
load_dotenv()

MODEL = os.environ.get("HARNESS:MODEL", "qwen3.5:latest")

_ollama = ollama.AsyncClient()
#Messages is how we do handle context
async def loop(client, messages, on_event=None):
    
    """
    THIS SECTION IS FOR WEBSOCKET HANDLING AND CONTEXT HANDLING.
    """
    #tools!
    tools = await get_tools(client)
    for _ in range(15):
        #extremely primitive way to handle
        full_content = ""
        tool_calls = []

        if on_event:
            await on_event("stream_start", "")

        async for chunk in await _ollama.chat(
            #so _ollama.chat() returns a stream. The stream is sent in "chunks"
            #each chunk is "message:, done:"
            #each message is "role: content:"


            model=MODEL,
            messages = messages,
            stream = True,
            tools = tools,

        ):
            token = chunk["message"]["content"]
            #this will be the content streamed.
            full_content += token

            if chunk["message"].get("tool_calls"):
                tool_calls = chunk["message"]["tool_calls"]
            if on_event:
                await on_event("stream_token", token)

        if on_event:
            await on_event("stream_end", "")

        if tool_calls:
            messages.append({
                "role": "assistant",
                "content": full_content,
                "tool_calls":[
                    {"function":{"name": tc.function.name, "arguments":dict(tc.function.arguments)}}
                    for tc in tool_calls
                ]
            })

            for tc in tool_calls:
                result = await client.call_tool(tc.function.name, dict(tc.function.arguments))
                result_text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
                messages.append({"role": "tool", "content": result_text})

        else:
            #This is the important bit. Appends context. there is a way to deal with needless context later,
            #but we haven't gotten that far

            messages.append({"role":"assistant", "content": full_content})
            if on_event:
                await on_event("message", full_content)
            return

"""Getting tools!!!"""
async def get_tools(client):
    mcp_tools = await client.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name":t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,

            },

        }
        for t in mcp_tools
    ]
