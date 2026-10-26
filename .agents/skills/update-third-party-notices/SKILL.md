---
name: update-third-party-notices
description: "This SOP guides the process of recording third-party content or code — agent skills, scripts, documents, or configurations — reused in this repository, either verbatim or modified, so that the repository stays compliant with all upstream licenses and with the REUSE Specification. It updates every compliance artifact: the license text under `LICENSES/`, a `LICENSE` sidecar next to the reused content, the `license` frontmatter field for skills, the entries in `THIRD-PARTY-NOTICES.md`, and the annotations in `REUSE.toml`, and finishes with a `uvx reuse lint` validation. Use it whenever third-party content is added, for example the planned custom opencode agent based on a modified ponytail agent skill."
---

# Update Third-Party Notices

## Overview

This SOP guides the process of recording third-party content or code — agent skills, scripts, documents, or configurations — reused in this repository, either verbatim or modified, so that the repository stays compliant with all upstream licenses and with the REUSE Specification. It updates every compliance artifact: the license text under `LICENSES/`, a `LICENSE` sidecar next to the reused content, the `license` frontmatter field for skills, the entries in `THIRD-PARTY-NOTICES.md`, and the annotations in `REUSE.toml`, and finishes with a `uvx reuse lint` validation. Use it whenever third-party content is added, for example the planned custom opencode agent based on a modified ponytail agent skill.

## Parameters

- **upstream_url** (required): URL of the upstream project the content comes from
- **license_id** (required): SPDX identifier of the upstream license (for example `MIT` or `Apache-2.0`)
- **content_path** (required): path or paths of the reused content inside this repository
- **status** (required): `verbatim` or `modified`
- **upstream_copyright** (optional): the upstream copyright line(s); derived from the upstream LICENSE or NOTICE file if not provided
- **notice_text** (optional): verbatim content of the upstream NOTICE file, when the project ships one
- **modification_summary** (optional): what changed relative to upstream; must be provided when status is `modified`

**Constraints for parameter acquisition:**
- If all required parameters are already provided, You MUST proceed to the Steps
- If any required parameters are missing, You MUST ask for them before proceeding
- When asking for parameters, You MUST request all parameters in a single prompt
- When asking for parameters, You MUST use the exact parameter names as defined
- You MUST NOT treat an unknown or missing license as MIT by assumption, because this repository is MIT-licensed and wrong attribution breaks license compliance
- When status is `modified`, You MUST also require `modification_summary`, because Apache-2.0 §4(b) requires a statement of what changed
- You MUST confirm successful acquisition of all parameters before proceeding

## Steps

### 1. Verify the upstream license facts

Confirm the license, the copyright holder, and any NOTICE file directly from the upstream repository (its LICENSE, NOTICE, and README files).

**Constraints:**
- You MUST obtain the SPDX identifier of the upstream license from the upstream repository, because every later artifact depends on it
- You MUST capture the upstream copyright and, when upstream ships a NOTICE file, its content verbatim, because Apache-2.0 §4(d) requires redistributions to carry it
- You MUST NOT proceed when the license is unknown, because obligations that were never read cannot be honored
- You MUST stop and ask the user when the license is copyleft (GPL family), because this repository is MIT-licensed and GPL code cannot be relicensed under MIT
- You SHOULD record the upstream source path of each reused file, because the per-file sources belong in THIRD-PARTY-NOTICES.md

### 2. Add the full license text to LICENSES/

Ensure `LICENSES/<SPDX-ID>.txt` exists with the complete license text.

**Constraints:**
- You MUST create `LICENSES/<SPDX-ID>.txt` when it is missing, because `uvx reuse lint` fails without the corresponding license text
- You MUST obtain the text from an authoritative source — the license's official URL, `uvx reuse download --all`, or this repository's own LICENSE file for MIT — because retyping legal text invites transcription errors
- You MUST NOT modify existing license texts under `LICENSES/`, because they are verbatim legal documents

### 3. Place the content with its notices

Treat the two statuses differently. Verbatim copies stay byte-identical to upstream and only get recorded; modified derivatives additionally carry a `LICENSE` sidecar next to the content.

**Constraints:**
- When status is `verbatim`, You MUST keep every file byte-identical to upstream, because unmodified files stay diffable and trigger no modification obligations
- When status is `verbatim`, You MUST NOT add headers, frontmatter, or attribution text to the copied files, because any change turns them into modified derivatives
- When status is `modified`, You MUST create a `LICENSE` sidecar file in the same directory as the content stating the upstream copyright, your copyright for the modifications, and what changed, because Apache-2.0 §4(b) requires prominent modification notices
- When status is `modified`, You MUST keep the content under its upstream license, because derivatives cannot be relicensed
- For skills that are modified derivatives, You MUST set the `license` field in the `SKILL.md` frontmatter (for example `license: Apache-2.0`), because it is the Agent Skills spec's machine-readable license field
- You MUST NOT put attribution text into the body of a `SKILL.md`, because the whole file is loaded into the agent's context and noise degrades agent performance

### 4. Update THIRD-PARTY-NOTICES.md

Add or update the entry for the upstream project in `THIRD-PARTY-NOTICES.md`.

**Constraints:**
- You MUST record the upstream project URL, the upstream copyright, the license, and the status of each reused file, because this file is the attribution source of truth for the repository
- You MUST quote the upstream NOTICE content verbatim in the entry when `notice_text` was provided, because Apache-2.0 §4(d) requires it
- You SHOULD follow the existing section and table format of the file, because consistency keeps the notices scannable

### 5. Update REUSE.toml

Add annotations for every file that carries no in-file SPDX headers.

**Constraints:**
- You MUST add an annotation with the copyright lines and the SPDX identifier for each new file, because `uvx reuse lint` fails on uncovered files
- You MUST use the upstream copyright for third-party files and this repository's copyright for original files, because copyright attribution must match authorship
- You SHOULD group files by license in the annotation lists, because the file stays readable as it grows

### 6. Validate with `uvx reuse lint`

Run the compliance gate and fix every finding.

**Constraints:**
- You MUST run `uvx reuse lint` after all edits, because it is the compliance gate for this repository
- You MUST fix every finding it reports before finishing, because partial compliance is non-compliance
- You MUST run `uvx reuse lint` again after each fix until it reports full compliance, because fixes can cascade (one added file can expose another uncovered one)
- You SHOULD re-read every file you created or edited, because both tools and agents make mechanical mistakes

### 7. Report

Summarize the result for the user.

**Constraints:**
- You MUST report which files were created or edited and the final `uvx reuse lint` result, because the user reviews before committing
- You SHOULD point out anything deliberately left untouched, such as verbatim upstream files, because that is part of the compliance decision

## Examples

### Example 1: Modified ponytail agent skill (MIT)

**Input:**
- upstream_url: https://github.com/dietrichgebert/ponytail
- license_id: MIT
- content_path: .opencode/agent/ponytail-lazy.md
- status: modified
- upstream_copyright: (the copyright line from ponytail's LICENSE file)
- modification_summary: adapted the ponytail SKILL.md prompt into a custom opencode agent definition

**Expected Behavior:**
The agent verifies the ponytail license (MIT) and its copyright line, confirms `LICENSES/MIT.txt` already exists, creates a `LICENSE` sidecar next to the opencode agent file with the ponytail copyright and the modification statement, lists the agent in the ponytail section of `THIRD-PARTY-NOTICES.md`, annotates the file in `REUSE.toml` as MIT with both copyrights, and finishes with a passing `uvx reuse lint`.

### Example 2: Verbatim Apache-2.0 skill copy

**Input:**
- upstream_url: https://github.com/strands-agents/agent-sop
- license_id: Apache-2.0
- content_path: .agents/skills/agent-sop-author/
- status: verbatim
- upstream_copyright: Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
- notice_text: Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

**Expected Behavior:**
The agent changes none of the copied files, creates only the `LICENSE` sidecar describing the verbatim copy, records the entry and the NOTICE quote in `THIRD-PARTY-NOTICES.md`, annotates the upstream files in `REUSE.toml` as Apache-2.0, and finishes with a passing `uvx reuse lint`. This is how `.agents/skills/agent-sop-author` was originally recorded; it was later modified in place (frontmatter conformance, then the rework to generate agent skills), so it now follows the modified-derivative treatment shown in `THIRD-PARTY-NOTICES.md`.

### Example 3: GPL-licensed snippet (stop)

**Input:**
- upstream_url: https://example.com/gpl-project
- license_id: GPL-2.0-only
- content_path: src/vendor/cool.c
- status: verbatim

**Expected Behavior:**
The agent stops before copying anything and asks the user, because GPL-2.0-only code cannot be relicensed under this repository's MIT license. No files are created and no compliance artifacts are updated.

## Troubleshooting

### The upstream license cannot be determined
Do not guess, because a wrong SPDX identifier corrupts every downstream artifact. Ask the user, and if the license stays unknown, do not add the content at all.

### Upstream ships a NOTICE file
Quote its content verbatim in `THIRD-PARTY-NOTICES.md` (Apache-2.0 §4(d)); naming only the project is not enough.

### `uvx reuse lint` reports a missing license
Add the full license text as `LICENSES/<SPDX-ID>.txt`; for MIT you can copy this repository's own `LICENSE`, and `uvx reuse download --all` fetches the rest.

### `uvx reuse lint` reports a file without copyright information
Add the file to the matching annotation group in `REUSE.toml` — `.gitignore` needed exactly this fix when compliance was first set up.

### `uvx` fails with "Read-only file system" under `~/.local/share/uv`
Redirect uv's writable directories to `/tmp`, for example `UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools UV_PYTHON_INSTALL_DIR=/tmp/uv-python uvx reuse lint`, because sandboxed terminals cannot write to the home directory.

### Cannot decide between verbatim and modified
If a single byte changed — even just added frontmatter — the content is modified and needs the modified-derivative treatment. This is exactly what happened to `.agents/skills/agent-sop-author`: it started as a verbatim copy, and adding the Agent Skills frontmatter (including the `license` field) turned it into a modified derivative.
