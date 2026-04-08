import asyncio
from fastmcp import Client


#local imports
from harness.utils.llm import loop
from harness.utils.logger import log_thinking


#System prompt
messages = [{
    "role": "system", 
    "content": "You MUST respond with tool_calls, never fake a tool result in text. If the user asks you to call a tool, respond ONLY with the tool call, no text."
}]



async def main():
    client = Client("http://localhost:8000/mcp")
    async with client:

        while True:
            user_input = input("\nTask: ")
            messages.append({"role": "user", "content": user_input})
            await loop(client, messages)



if __name__ == "__main__":
    asyncio.run(main())