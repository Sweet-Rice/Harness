# Harness



My DIY LLM Harness to hopefully one day outdo Claude Code. I will surpass Opus.


# Context Model High Level Overview

- Ingest files one by one, mapping functions in each file to a highlevel, javadoc like structure. 
- On each post primary ingestion, expand the mapped function description.
- Every ten loops of the agent where a file was not accessed, ingest the least accessed function and compress the context description. Reset last_accessed.


# Custom Tooling

Hopefully implementing tools myself will help me understand the plumbing.

Eventually, I hope to have an expansive MCP server that allows multi-agent control for preventing context drift and hallucinations.


