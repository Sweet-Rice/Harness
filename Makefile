PYTHON := .venv/bin/python
PIP := .venv/bin/pip
NPM := npm
WEB_DIR := harness/web/client

.PHONY: help install build rebuild lint mcp cli web ui dev clean

help:
	@printf "%s\n" \
		"make install  - install Python and web dependencies" \
		"make build    - build the web client" \
		"make rebuild  - syntax-check Python and rebuild the web client" \
		"make mcp      - run the MCP server" \
		"make cli      - run the terminal harness" \
		"make web      - run the web bridge/server" \
		"make ui       - start MCP in background and run the web bridge" \
		"make dev      - start MCP in background and run the terminal harness"

install:
	$(PIP) install -e .
	$(NPM) --prefix $(WEB_DIR) install

build:
	$(NPM) --prefix $(WEB_DIR) run build

lint:
	$(PYTHON) -m py_compile harness/*.py harness/utils/*.py harness/tools/*.py harness/web/*.py

rebuild: lint build

mcp:
	$(PYTHON) -m harness.server

cli:
	$(PYTHON) -m harness.harness

web:
	$(PYTHON) -m harness.web.server

ui: rebuild
	sh -c 'OWNED=0; if $(PYTHON) -c "import socket; s=socket.socket(); s.settimeout(0.3); raise SystemExit(0 if s.connect_ex((\"127.0.0.1\", 8000)) == 0 else 1)"; then echo "Reusing existing MCP server on :8000"; else trap "if [ $$OWNED -eq 1 ]; then kill $$MCP_PID; fi" EXIT; $(PYTHON) -m harness.server & MCP_PID=$$!; OWNED=1; READY=0; for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do if $(PYTHON) -c "import socket; s=socket.socket(); s.settimeout(0.3); raise SystemExit(0 if s.connect_ex((\"127.0.0.1\", 8000)) == 0 else 1)"; then READY=1; break; fi; if ! kill -0 $$MCP_PID 2>/dev/null; then echo "MCP server exited before becoming ready"; exit 1; fi; sleep 0.5; done; if [ $$READY -ne 1 ]; then echo "Timed out waiting for MCP server on :8000"; exit 1; fi; fi; $(PYTHON) -m harness.web.server'

dev: rebuild
	sh -c 'OWNED=0; if $(PYTHON) -c "import socket; s=socket.socket(); s.settimeout(0.3); raise SystemExit(0 if s.connect_ex((\"127.0.0.1\", 8000)) == 0 else 1)"; then echo "Reusing existing MCP server on :8000"; else trap "if [ $$OWNED -eq 1 ]; then kill $$MCP_PID; fi" EXIT; $(PYTHON) -m harness.server & MCP_PID=$$!; OWNED=1; READY=0; for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do if $(PYTHON) -c "import socket; s=socket.socket(); s.settimeout(0.3); raise SystemExit(0 if s.connect_ex((\"127.0.0.1\", 8000)) == 0 else 1)"; then READY=1; break; fi; if ! kill -0 $$MCP_PID 2>/dev/null; then echo "MCP server exited before becoming ready"; exit 1; fi; sleep 0.5; done; if [ $$READY -ne 1 ]; then echo "Timed out waiting for MCP server on :8000"; exit 1; fi; fi; $(PYTHON) -m harness.harness'

clean:
	rm -rf harness/web/static/assets
