# Tests

Test suites for the things in this repository. Run them all with:

```bash
make test          # or: tests/run.sh
```

## Layout

- `run.sh` — entry point that discovers and runs every suite in this tree
- `lib.sh` — shared assertion helpers (`assert_grep`, `assert_rc`, `finish`, ...)
- `skills/<skill>/` — suites for one skill, with a local `lib.sh` fixture

A suite is any `test-*.sh` file anywhere under `tests/`. It sources the
assertion helpers (usually through its local `lib.sh`), runs checks with the
`assert_*` helpers, and ends with `finish`, which prints a per-suite summary
and makes the suite exit non-zero on any failure.

Suites whose basename starts with `test-e2e` are live end-to-end tests:
they run real `opencode` sessions, need authentication, and spend model
tokens. They are skipped by default and only run with `--e2e`:

```bash
test-e2e
make test-e2e # or: tests/run.sh --e2e (hermetic + e2e)
tests/run.sh --e2e-only   # just the e2e suites
```

The e2e suites are cheap smoke tests (tiny prompts, cheapest model). Full
reviews are deliberately not automated — a real review spends serious
reasoning money; the full `run-review.sh` execution path is covered
hermetically by a stubbed-opencode test, and a real review can be exercised
by running the skill itself. The e2e model defaults to
`mistral/zai-glm-5-3-flash` and can be overridden with the `E2E_MODEL` and
`E2E_REASONING_EFFORT` environment variables, for example:

```bash
E2E_MODEL=mistral/zai-glm-5-3 E2E_REASONING_EFFORT=max tests/run.sh --e2e-only
```

## Conventions

- Hermetic suites must not touch the network, spend tokens, or modify
  anything outside the test workspace.
- Suites rebuild their own fixture repositories (see the per-suite
  `setup_repo`) inside the repository's gitignored `.local/` and leave them
  there for inspection after a run.
- When adding a new suite, only the `test-*.sh` file name convention is
  required; `run.sh` picks it up automatically.
