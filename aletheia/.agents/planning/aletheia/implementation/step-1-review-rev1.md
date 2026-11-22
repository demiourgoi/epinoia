# Ponytail review — implementation step 1 — round 1

> Review subject: `code-commits`, commit `12f5e31` ("step 1 project
> skeleton"). The `opencode` runner is unavailable in this sandbox, so this
> review was produced by the implementing agent applying the ponytail
> checklist to the commit diff (tools read: pyproject.toml, Makefile,
> src/aletheia_mcp/**, tests/**).

What this change does: it stands up the aletheia package — Python 3.14
pinned, hatchling/uv packaging, cyclopts `aletheia` command running a
FastMCP stdio server with a placeholder ping tool, settings, error classes,
Makefile, tests.

Checked: packaging claim (`requires-python >=3.14,<3.15`, console script
`aletheia = aletheia_mcp.main:app`, wheel target `src/aletheia_mcp`);
imports resolve on 3.14; the client test drives the real server instance;
the error-class messages match the design's "written for an agent" rule.

**Must fix:**

1. **The ping tool is registered via an eager call at import time**
   (`src/aletheia_mcp/server/server.py`, `_register_tools()`). What this
   is: module-level side effect wiring. Problem: importing `server.server`
   twice (e.g. under a reloader or a test import) registers the tool again,
   and the function/`__all__` ordering is a source of import loops later.
   Fix: register tools with decorators on `mcp` in the tools modules
   (FastMCP's standard pattern) and drop `_register_tools`. If we skip it:
   the first real tools added in step 3 risk duplicate registration
   warnings and import-order bugs.

**Should fix:**

2. **`ping` lives in `server/tools/system.py` but the plan says tools get
   registered per module. Problem: after fix 1 the module needs `__all__` and
   an import by `server.server` (or a provider). Fix while refactoring: let
   importing the tools package register its tools (decorator modules
   imported from `server/__init__`). One line, keeps step 3 additive.

Verdict: fix 1 and 2 first.
