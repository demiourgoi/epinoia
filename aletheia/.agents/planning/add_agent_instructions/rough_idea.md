I have done some tests for aletheia, and I have found that adding the instructions in ~/.vibe/AGENTS.md is what works better with Vibe, when combined with "2. Forbid the built-in edit and write_file tools (recommended)". Add that as a step 3 of "Mistral Vibe setup". 
Then change "Optionally install the reminder hook (fallback)" as an alternative solution, but make clear that that does not work so well

Then change [@main.py (21:41)](file://~/git/demiourgoi/epinoia/aletheia/src/aletheia_mcp/main.py#L21:41)  to automate that main setup: register MCP server, built-in edit and write_file tools, and add the text currently in to `~/.vibe/AGENTS.md`, and remove the installation of the hook

- Make sure that that setup is idempotent, and respect other content in the relevant files
- Document that the setup can be automated with the `setup` command of aletheia
- How can we make sure that when used with `uvx` the setup command uses the variant [@README.md (83:86)](file://~/git/demiourgoi/epinoia/aletheia/README.md#L83:86) , and otherwise uses [@README.md (71:79)](file://~/git/demiourgoi/epinoia/aletheia/README.md#L71:79) ?
