# Design: automate the Aletheia–Vibe setup

Status: implemented. Scope: `aletheia/` (`README.md`,
`DEVELOPER_GUIDE.md`, `pyproject.toml`, `src/aletheia_mcp/{main,setup,__init__}.py`,
`tests/unit/{test_setup,test_main}.py`) and the command tables in
`AGENTS.md` / `aletheia/AGENTS.md`.

## Problem

Field testing showed what actually makes an agent edit through Aletheia in
Mistral Vibe is a **combination**:

1. the `aletheia` MCP server registered in `config.toml`;
2. Vibe's built-in `edit` and `write_file` tools **disabled**
   (`disabled_tools = ["edit", "write_file"]`);
3. an explicit editing policy in `AGENTS.md` telling the agent to use
   `aletheia_edit` and to surface the review URL.

The setup the repository shipped was neither of those: `aletheia setup`
installed only a **reminder hook** (a `post_tool` hook that nudges the agent
after an edit). That hook is best-effort — it runs in a separate process,
cannot see the in-memory baseline, and only asks the agent to record
changes after the fact — so agents frequently ignored it. The README also
presented the hook as step 3 and the built-ins as merely "recommended",
which inverted the priority the field tests established.

Goals, from `rough_idea.md`:

- Make the AGENTS.md instructions step 3 of "Mistral Vibe setup".
- Demote the reminder hook to an explicit alternative, clearly marked as
  not working as well.
- Automate the main setup in `aletheia setup`: register the MCP server,
  disable the built-in `edit`/`write_file`, add the AGENTS.md text — and
  stop installing the hook by default.
- The setup must be **idempotent** and must **preserve unrelated content**.
- Document that `aletheia setup` automates the manual steps.
- Make the `uvx` variant of the MCP server registration automatic when
  `setup` itself runs under `uvx`, and the installed-script variant
  otherwise.

## Decisions

### 1. `aletheia setup` writes the recommended setup, not the hook

`setup` now performs the three README steps. The hook moved behind
`--legacy-hook`, which keeps every previous behaviour reachable while the
default stops installing something the field tests show is inferior. This
is a deliberate behaviour change for existing users: rerunning `setup`
after upgrading will not touch their existing `hooks.toml` (the legacy path
is opt-in), but it will now also write `config.toml` and `AGENTS.md`.

The command targets the **git root** by default (unchanged rationale: Vibe
walks `AGENTS.md` up to the trusted folder's root and loads project config
from there; a subdirectory install can be invisible), or `~/.vibe` with
`--global`.

### 2. Surgical, idempotent edits via tomlkit

`config.toml` is a real, hand-maintained file: it holds models, providers,
other MCP servers and comments. Appending text blindly would duplicate
blocks and break on reruns. We therefore parse and modify with
[tomlkit](https://tomlkit.readthedocs.io/) (new dependency), which keeps
comments, ordering and formatting:

- **MCP server**: `merge_mcp_server` finds our entry by `name = "aletheia"`
  and reuses it, updating only `command`/`args`. It understands the layouts
  in use — top-level `[[mcp_servers]]`, nested
  `[[model_providers.<name>.mcp_servers]]`, `[mcp_servers.<name>]`
  subtables, and a file with no `mcp_servers` key (append a top-level
  `[[mcp_servers]]`). It never retargets an entry the user pointed
  elsewhere: an `aletheia` entry with `transport != "stdio"` is left alone.
- **Disabled tools**: `merge_disabled_tools` creates `disabled_tools` or
  extends an existing array, so a tool the user already disabled is never
  dropped. Multi-line formatting is used for readability.
- **AGENTS.md**: `merge_agents_md` writes the policy between
  `<!-- aletheia:begin ... -->` and `<!-- aletheia:end -->` markers. Absent,
  it is appended; present, it is replaced in place, so reruns converge and
  user prose around it is untouched.

`tomllib` (stdlib) validates a pre-existing `config.toml` before any write
and the command refuses (with a clear message) rather than rewrite a file
it cannot parse. `install()` returns one line per file (`created` /
`updated` / `unchanged`), which makes idempotency observable and testable.

### 3. `uvx` vs installed-script variant, detected, not guessed

The two README variants exist because a `uvx` run's environment is
temporary: once `aletheia setup` exits, the environment that ran it is
destroyed, so registering `command = "aletheia"` would break. When `setup`
ran under `uvx` we must register `command = "uvx"`.

Detection is empirical, not heuristic-by-name. `uvx` and `uv tool run`
unpack into `<cache>/archive-v0/` and run the tool's interpreter from
there; an installed script (venv, `pipx`, wheel) runs from its own
environment. So `main._launched_by_uvx()` returns whether
`sys.executable` has an `archive-v0` path component — verified directly
against both `uvx` and `uv tool run`, and against a local `.venv` (which
has none). This is in `main.py` because it is a property of *how this
process was started*, while `setup.server_command(launched_by_uvx)` is a
pure function that maps that fact to `(command, args)`, keeping `setup.py`
easy to test.

### 4. The `uvx` variant names a distribution we own

While validating the uvx path we found that **`aletheia` on PyPI is an
unrelated 2021 AGPL project**, and **`aletheia-mcp` is an unrelated
2026 scientific-literature MCP**; the README's `uvx --from aletheia
aletheia` would have installed a stranger's package. `epinoia-aletheia`
is free. The distribution is therefore renamed to `epinoia-aletheia`
(the console script stays `aletheia`, which is what hosts reference), and
the uvx variant uses `args = ["--from", "epinoia-aletheia", "aletheia"]`.
`__version__` and the version test follow the renamed distribution.

## Alternatives considered

- **Append text to `config.toml` / `AGENTS.md`** (as the old hook installer
  did for `hooks.toml`): no new dependency, but breaks on reruns (duplicate
  tables) and cannot update an existing entry. Rejected.
- **Use `vibe mcp add` / `vibe config` subcommands**: would delegate the
  edit to Vibe, but requires Vibe to be installed, offers no guarantee of
  preserving other content, and cannot write `AGENTS.md`. Rejected.
- **Disable built-ins via `[tools.edit] permission = "never"`**: equivalent
  per the Vibe reference, but `disabled_tools` is a single, mergeable list;
  we use that.
- **Make the hook the default and AGENTS.md optional**: contradicted by
  the field tests. Rejected; the hook is now the opt-in fallback.
- **Detect uvx by inspecting `sys.argv[0]` / `UV_*` env vars**: `argv[0]`
  is the console script in both cases, and the `UV_*` set is not
  equivalent between `uvx` and `uv tool run`. The interpreter path is the
  reliable signal.

## Consequences

- New runtime dependency: `tomlkit` (MIT). No third-party *content* is
  copied, so `THIRD-PARTY-NOTICES.md` / REUSE are unchanged.
- Users who relied on `setup` installing the hook must pass
  `--legacy-hook`; the README and developer guide say so.
- `aletheia setup` now edits two files (`config.toml`, `AGENTS.md`);
  re-running is safe and reports `unchanged`.
- Publishing under `epinoia-aletheia` is a prerequisite for the `uvx`
  variant to resolve to our code rather than a namesake.

## Validation

- `make -C aletheia check` (ruff, ruff format, mypy) — clean.
- `make -C aletheia test` — 122 tests pass. New coverage in
  `tests/unit/test_setup.py`: create/idempotent, unrelated content and
  comments preserved, managed section refreshed in place, invalid TOML
  refused, uvx variant, variant switched on rerun, each `mcp_servers`
  layout, non-stdio `aletheia` left alone, `disabled_tools` merge and type
  error, CLI at git root, `--legacy-hook`, and `_launched_by_uvx` detection.
- End-to-end with a real `uvx`: `uvx --from epinoia-aletheia ... aletheia
  setup --global` against a throwaway `HOME` wrote
  `command = "uvx"`, `args = ["--from", "epinoia-aletheia", "aletheia"]`,
  `disabled_tools = ["edit", "write_file"]` and the AGENTS.md section, and
  a second run reported `unchanged` for both files.

Notes for whoever picks this up:

- A `uv tool run` / `uvx` environment can be cached across runs keyed by
  the requirement, not the wheel contents; during validation a rebuilt
  wheel was masked by a stale cached environment until the uv cache was
  cleared. When testing a newly built wheel, clear or isolate the cache.
- The sandbox needs `UV_CACHE_DIR` pointing at a writable directory for
  `uv`/`uvx` to work here; the aletheia `AGENTS.md` records this.
