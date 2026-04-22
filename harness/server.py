from fastmcp import FastMCP

import importlib
import pkgutil

from harness.utils.config import SETTINGS

#local imports
import harness.tools 


mcp = FastMCP("harness")




#Server.py exists just as a source of truth for the llm to call tools.

for finder, name, ispkg in pkgutil.iter_modules(harness.tools.__path__):
    #name  is each file name
    module = importlib.import_module(f"harness.tools.{name}")
    for func in getattr(module, "TOOLS", []):
        mcp.tool()(func)

if __name__=="__main__":
    mcp.run(
        transport="http",
        host=SETTINGS.mcp_host,
        port=SETTINGS.mcp_port,
    )
