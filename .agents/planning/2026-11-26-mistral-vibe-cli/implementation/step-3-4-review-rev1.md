# Steps 3 + 4 Review — rev1

Reviewer: ponytail-review, applied to the compliance changes
(`REUSE.toml`) and the new CI workflow (`.github/workflows/tests.yml`).

**What this change does:** Registers the new files (`SKILL.md`, the workflow,
the PDD artifacts) in `REUSE.toml` as original MIT content, and adds a CI
workflow with two jobs — the root hermetic suites (`make test`) and the
aletheia pytest suite — on pull requests and pushes to main.

## Checks done

- `reuse lint` passes; the only annotation catch was a literal
  "SPDX-License-Identifier" string quoted inside the design document, which
  reuse treats as an in-file header (the REUSE.toml NOTE documents this
  behavior for Copyright lines). Reworded to prose.
- The workflow YAML parses; triggers cover PRs and merges (push to main);
  `permissions: contents: read` is least-privilege.
- The root job installs `opencode-ai` globally first, because the
  hermetic ponytail-review-pdd suites require the binary even for dry runs —
  verified in this environment: without the binary the suites fail, with it
  they pass. `make test-e2e` is correctly left out (needs opencode auth and
  spends model tokens).
- The aletheia job uses the project's own targets (`make install`, `make
  test`) with `setup-uv` and Python 3.14; the identical command sequence
  passes locally (97 tests).

## Findings

- **Should fix:** none blocking. One consideration: the aletheia job does not
  run `make check` (mypy/ruff) or the web UI build — the request was tests
  only, so they stay out; adding them later is a one-line step per extra
  target.
- **Nice to have:** the workflow could pin `opencode-ai` to a major version
  (`opencode-ai@1`) to avoid a breaking CLI rename mid-life; the README of
  the upstream project has kept the binary name stable, and the hermetic
  suites only need the binary to exist, so `@latest` is acceptable.

Looks good. **Verdict: Ship.**

**Not checked:** actual GitHub Actions execution (requires a push to
GitHub); the jobs mirror commands verified green locally.
