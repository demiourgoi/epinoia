# Ponytail review — implementation step 1 — round 2

> Same setup as round 1; round‑1 fixes (decorator-based tool registration,
   no import-time side effect) verified in the code first.

What this change does (post-fix): identical skeleton, with tools now
registered by decorator on the shared `mcp` instance when the tools package
is imported from `aletheia_mcp.server.__init__`; the server module has no
eager registration call.

Checked: `python -c "import aletheia_mcp.server; from fastmcp import Client;
Client(aletheia_mcp.server.mcp)"` sees the ping tool once; re-import paths
(sys.modules reuse) register nothing twice; `make check` / `make test` green.

Looks good. Ship.
