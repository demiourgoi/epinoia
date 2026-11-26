"""Aletheia baseline reminder hook (installed by `aletheia setup`).

Reads the Vibe CLI post_tool payload from stdin and, when an editable file
was touched, appends a reminder to the tool output the model sees, so the
review baseline stays current. Best effort only: the hook runs in its own
process and cannot inspect the MCP server's in-memory baseline.
"""

import json
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(payload, dict) or payload.get("tool_status") != "success":
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("filename")
    if not isinstance(path, str) or not path.strip():
        return
    reminder = (
        f"Aletheia: '{path}' was just edited. If it is not yet in the review "
        "baseline, call record_baseline with this path now, so the user can "
        "review your edits in the Aletheia web UI."
    )
    print(json.dumps({"hook_specific_output": {"additional_context": reminder}}))


if __name__ == "__main__":
    main()
