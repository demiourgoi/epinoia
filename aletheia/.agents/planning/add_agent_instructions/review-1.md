# Review: uncommitted changes in `aletheia/` ( automate the Aletheia–Vibe setup)

Reviewed per `skills/ponytail-review/SKILL.md`. Scope: all uncommitted changes under
`aletheia/` plus the `AGENTS.md` command table that belongs to them, against the plan in
`.agents/planning/add_agent_instructions/`. Expected load assumed: one user running the
`aletheia setup` CLI by hand; no concurrency.

**What this change does:** `aletheia setup` stops installing the reminder hook by default and
instead writes the recommended Vibe setup: it registers the `aletheia` MCP server in
`config.toml`, adds `edit`/`write_file` to `disabled_tools`, and appends an editing policy to
`AGENTS.md` between markers — all surgically via tomlkit, idempotent, preserving unrelated
content. The PyPI distribution is renamed to `epinoia-aletheia` (the console script stays
`aletheia`), and the `uvx` launch variant is chosen automatically when `setup` itself runs
under `uvx`. README, developer guide, and both AGENTS.md command tables follow. I ran
`UV_CACHE_DIR=.local/uv-cache make check` and `make test` in `aletheia/`: clean, 122 tests
pass.

## Must fix

1. **Non-uvx setup registers a command Vibe may not be able to launch**
   (`aletheia/src/aletheia_mcp/setup.py`: `LOCAL_COMMAND`, `server_command`;
   `aletheia/src/aletheia_mcp/main.py`: `setup`)
   - **What this is:** When `setup` did not run under `uvx`, it registers
     `command = "aletheia"` — a bare name, resolved through `PATH` when Vibe spawns the
     server.
   - **Problem:** The package is not on PyPI yet, so today the only ways to run
     `setup` are from the checkout (`uv run aletheia setup`, the very command
     `aletheia/AGENTS.md` documents) or a local `pipx`/`uv tool install` of it. The
     from-checkout flow writes the bare name, but the checkout's
     `.venv/bin/aletheia` is not on `PATH` when Vibe starts. Vibe cannot launch the
     server, the built-ins are disabled in the same run, so the agent has no way to
     edit files at all. The README's manual step 1 says to use the *absolute path*
     for exactly this reason; the automation is weaker than the instructions it
     automates. Pre-release this is the primary path, not a corner case.
   - **Fix:** Register the resolved path of the console script that is running (for example
     `Path(sys.argv[0]).resolve()`), like README step 1 does. Keep the bare name only if it
     resolves on `PATH` (for `pipx`/`uv tool install`, where it does).
   - **If we skip it:** Anyone setting up from a clone (not `pipx`, not `uvx`) gets a config
     that silently breaks the MCP server on Vibe restart — the worst failure mode, because
     `disabled_tools` removes the fallback.

## Should fix

2. **An existing `aletheia` entry without `transport` is skipped silently**
   (`aletheia/src/aletheia_mcp/setup.py`: `_upsert`, `_upsert_named`)
   - **What this is:** A pre-existing `aletheia` entry is only updated when it says
     `transport = "stdio"`. Without that key it is left alone — by design for non-stdio
     entries, but also when the key is simply missing.
   - **Problem:** I confirmed it: an entry `[[mcp_servers]] name = "aletheia"
     command = "old"` survives `setup` unchanged, and the run still prints `unchanged` plus
     "Restart Vibe". The user believes setup succeeded while the server still points at the
     old command. (The Vibe reference marks `transport` as required, so such an entry is
     broken anyway — all the more reason not to report success over it.)
   - **Fix:** When an `aletheia` entry is found but skipped, print a warning naming the
     reason. One or two lines in `install()`/`_upsert`; no behavior change.
   - **If we skip it:** Setup reports success for a config that will not launch the server;
     with the built-ins disabled that again leaves no edit path.

3. **The knowledge base still teaches the old, now dangerous commands**
   (`.agents/summary/codebase_info.md`, `.agents/summary/dependencies.md`,
   `.agents/summary/interfaces.md`, `aletheia/.agents/summary/*`)
   - **What this is:** The change updates both AGENTS.md command tables but not the
     `.agents/summary/` files that route agents.
   - **Problem:** They still say `uvx --from aletheia aletheia` — which the design doc
     itself established resolves to an unrelated stranger's PyPI package — and still
     describe `aletheia setup` as installing the reminder hook. The root `AGENTS.md` rule is
     to update the summary directory in the same change as any command/convention change.
   - **Fix:** Update the affected lines in the summary files (distribution name, what
     `setup` does now, hook behind `--legacy-hook`).
   - **If we skip it:** The next agent or contributor following the summary runs a foreign
     package or the wrong setup command.

4. **The nested-provider scan covers a layout Vibe does not document — and only the first one**
   (`aletheia/src/aletheia_mcp/setup.py`: `merge_mcp_server` nested loop)
   - **What this is:** ~15 lines that search for `mcp_servers` arrays nested inside
     top-level tables, e.g. `[[model_providers.<name>.mcp_servers]]`.
   - **Problem:** The Vibe configuration reference documents `mcp_servers` only as a
     top-level array; there is no `model_providers` key at all (providers are `[[providers]]`,
     without nested servers), and this repo's own `.vibe/config.toml` has none. If no real
     config with that layout exists, the code is speculative; if one does, I confirmed it
     registers the server in the *first* provider only, so a second provider's sessions
     lose `aletheia_edit` while the built-ins stay disabled.
   - **Fix:** Either delete the nested scan (and its test branch) as undocumented, or — if
     the layout came from a real config — register in every provider that has an
     `mcp_servers` array, and record where the layout was seen.
   - **If we skip it:** Dead flexibility is read, tested, and fixed forever; or a real
     two-provider config is half-configured.

## Nice to have

5. **A missing end marker duplicates the policy section** (`setup.py`: `merge_agents_md`)
   - **What this is:** Replacement is keyed on finding both markers.
   - **Problem:** Confirmed: if the end marker was deleted (hand edit), a run appends a full
     second section — 2 begin markers, 1 end. It self-heals on the next run, so the damage
     is one duplicated policy in between.
   - **Fix:** Treat "begin found, end missing (or before begin)" as malformed: replace from
     `begin` to the end of the text.
   - **If we skip it:** A cosmetic duplicate that the next rerun fixes.

6. **README's step-3 block and the written policy differ slightly** (`aletheia/README.md`
   vs `AGENTS_SECTION` in `setup.py`)
   - **What this is:** The README shows the exact markdown `setup` supposedly writes.
   - **Problem:** The written bullet says "(Aletheia's MCP `edit`; your host may list it as
     `mcp_aletheia.edit`)", the README block says only "(your host may list it as
     `mcp_aletheia.edit`)". Small drift today, bigger later.
   - **Fix:** Make the README block a copy of `AGENTS_SECTION`, or generate the README block
     from it in a test.
   - **If we skip it:** The README slowly stops describing what the command writes.

7. **`--global` ignores `VIBE_HOME`** (`main.py`: `setup`)
   - **What this is:** `--global` always writes `~/.vibe`.
   - **Problem:** Vibe's reference documents `VIBE_HOME` as overriding the `~/.vibe` home
     for all state; a user who set it gets a "successful" setup Vibe never reads.
   - **Fix:** Use `os.environ.get("VIBE_HOME")` when set, else `Path.home() / ".vibe"`.
   - **If we skip it:** A niche configuration is misconfigured silently.

8. **One test line asserts nothing** (`aletheia/tests/unit/test_setup.py`:
   `test_merge_agents_md_creates_and_appends`)
   - **What this is:** `assert merge_agents_md("") == merge_agents_md("")` — trivially true
     for any deterministic function.
   - **Problem:** It cannot fail, so it guards nothing; the empty-file case is already
     covered by `test_install_creates_config_and_agents`.
   - **Fix:** Delete the line, or assert the result contains `AGENTS_BEGIN`.
   - **If we skip it:** One dead line in the suite.

## Verdict

- **Verdict: fix 1 first; 2–4 should follow before this ships.**
- **Lean: about −20 lines possible** (nested scan + test branch in finding 4, dead assert in
  finding 8), if finding 4 resolves to "delete".
- **Not checked:** whether Vibe accepts `[mcp_servers.<name>]` subtables in practice (the
  reference documents only `[[mcp_servers]]`; the code supports both, which is harmless);
  `_launched_by_uvx` was verified in the design doc on this machine only. Also expected and
  not a finding: until `epinoia-aletheia` is published, any config the `uvx` variant writes
  (`uvx --from epinoia-aletheia aletheia`) cannot launch — the design doc already lists
  publication as a prerequisite, so verify the launch command on a real install before
  announcing the release.
- **Pre-release note:** the distribution rename to `epinoia-aletheia` is what makes the
  future `uvx` variant safe (bare `aletheia` on PyPI is an unrelated AGPL project), so the
  rename should land before, not after, the first `uvx --from epinoia-aletheia` command
  anyone runs.
