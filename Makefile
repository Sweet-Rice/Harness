.PHONY: help mcp web discord stack dev check

help:
	@printf "Targets:\n"
	@printf "  make mcp      Start the FastMCP server\n"
	@printf "  make web      Start the web UI server\n"
	@printf "  make discord  Start the Discord bot\n"
	@printf "  make stack    Start the MCP server and web UI together\n"
	@printf "  make dev      Start MCP, web UI, and Discord together\n"
	@printf "  make check    Compile all Python files for a quick sanity check\n"

mcp:
	uv run python -m harness.server

web:
	uv run python -m harness.web.server

discord:
	uv run python -m harness.discord

stack:
	@trap 'kill 0' INT TERM EXIT; \
	uv run python -m harness.server & \
	uv run python -m harness.web.server & \
	wait

dev:
	@trap 'kill 0' INT TERM EXIT; \
	uv run python -m harness.server & \
	uv run python -m harness.web.server & \
	uv run python -m harness.discord & \
	wait

check:
	python3 -m py_compile $$(rg --files harness -g '*.py')
