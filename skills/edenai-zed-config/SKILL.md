---
name: edenai-zed-config
description: Generate a single Zed `settings.json` model entry for a model served by Eden AI, targeting the `language_models.openai_compatible` provider block. The SOP reads Zed's documentation for the authoritative field schema, reads the LiteLLM model catalog for context window, output limit, capabilities, and reasoning-effort support, and prints a ready-to-paste JSON object whose `name` is the Eden AI `model_id` exactly as supplied.  Use this SOP when adding an Eden AI model to Zed's agent panel, or when refreshing the limits of an existing entry.
---

# Eden AI Model Entry for Zed

## Overview

Generate a single Zed `settings.json` model entry for a model served by Eden AI, targeting the `language_models.openai_compatible` provider block. The SOP reads Zed's documentation for the authoritative field schema, reads the LiteLLM model catalog for context window, output limit, capabilities, and reasoning-effort support, and prints a ready-to-paste JSON object whose `name` is the Eden AI `model_id` exactly as supplied.

Use this SOP when adding an Eden AI model to Zed's agent panel, or when refreshing the limits of an existing entry.

## Parameters

- **model_id** (required): The model identifier exactly as exposed by the Eden AI API (for example `deepseek-v4.1-flash-1017`). This value is emitted verbatim as the `name` field and is the key used to look the model up in external catalogs.

**Constraints for parameter acquisition:**
- If all required parameters are already provided, You MUST proceed to the Steps
- If any required parameters are missing, You MUST ask for them before proceeding
- When asking for parameters, You MUST request all parameters in a single prompt
- When asking for parameters, You MUST use the exact parameter names as defined
- You MUST store `model_id` exactly as received, including dots, case, and snapshot suffixes, because the emitted `name` must match the string Eden AI expects at request time
- You MUST NOT lowercase, slugify, or strip provider prefixes from the received `model_id` because the emitted `name` must match the string Eden AI expects byte for byte

## Steps

### 1. Retrieve the Zed Configuration Schema

Access `https://zed.dev/llms.txt` and locate the reference that defines how an OpenAI-compatible LLM provider and its models are configured in Zed.

**Constraints:**
- You MUST fetch `https://zed.dev/llms.txt` first
- `https://zed.dev/llms.txt` is a site index, not the schema itself; if it does not contain field definitions, You MUST follow its documentation link to `https://zed.dev/docs` and open the API access page at `https://zed.dev/docs/ai/use-api-access`, section "OpenAI-Compatible Endpoints"
- You MUST extract the field names, required/optional status, and default values for entries under `language_models.openai_compatible.<provider>.available_models[]`
- You MUST treat the Zed documentation as the sole authority for which fields may appear because unknown or renamed settings are rejected or silently ignored
- You MUST NOT invent field names that the documentation does not define because Zed validates its settings schema and silently ignores unknown keys
- If the documentation cannot be retrieved or the referenced section has moved, You MUST report the failure and stop rather than guessing the schema

### 2. Download the LiteLLM Model Catalog

Fetch `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` into a temporary directory on disk.

**Constraints:**
- You MUST download the file to disk (for example with `curl` into a directory created by `mktemp -d`) because the catalog is several megabytes and would consume the entire context window if fetched as document text
- You MUST NOT pass the catalog URL to a document-fetch mechanism that returns the full body into the conversation since that floods the context window and leaves no room to analyse the result
- You MUST inspect the downloaded file with search tools such as `grep` or `jq`
- You MUST NOT print the entire catalog to the conversation as it contains thousands of entries that the reader does not need
- You SHOULD confirm the download succeeded and is non-empty before searching

### 3. Locate the Model Entry

Find the catalog entry that corresponds to `model_id`.

Catalog keys are namespaced as `<provider>/<model>`, and the model portion may use different separators or carry extra qualifiers, so the exact string is often absent.

**Constraints:**
- You MUST search in this order:
  1. Exact key match on `model_id`
  2. Suffix match on `/model_id`, since keys are prefixed with a provider
  3. Normalized match, comparing case-insensitively and treating `.`, `-`, and `p` as interchangeable separators (for example `deepseek-v4.1-flash-1017` may appear as `DeepSeek-V4.1-Flash-1017` or `deepseek-v4p1-flash-1017`)
  4. Family match on the base model name without the snapshot suffix, only if no snapshot-specific entry exists
- You MUST record which catalog key supplied the values and whether the match was exact, normalized, or a family match
- You MUST capture `supports_reasoning` and `reasoning_effort_levels` for every candidate entry because Step 4 needs them to choose the effort level
- You SHOULD prefer vendor-native provider keys (`deepseek/`, `moonshot/`, `zai/`) over reseller keys when the same model appears under several providers
- You MUST NOT silently substitute a different model generation because the numbers look plausible; a wrong generation invalidates every downstream value
- If several providers disagree, You SHOULD use the most conservative `max_output_tokens` and report the observed range
- If no entry matches, You MUST report the nearest candidates and ask whether to proceed rather than fabricating values
- You MAY apply an Eden AI-specific alias mapping when the user supplies one, but You MUST state that the mapping was applied

Example inspection command (replace the pattern with the literal search term; do not interpolate the raw `model_id` unescaped into a regex):

```bash
jq -r 'to_entries[]
  | select(.key | test("kimi-k3"; "i"))
  | [.key, (.value.litellm_provider // "-"),
     (.value.max_input_tokens // "-"), (.value.max_output_tokens // "-"),
     (.value.supports_function_calling // "-"), (.value.supports_vision // "-"),
     (.value.supports_reasoning // "-"),
     ((.value.reasoning_effort_levels // ["-"]) | join(","))]
  | join(" | ")' /tmp/model_prices_and_context_window.json
```

### 4. Map Catalog Fields to Zed Fields

Translate the catalog attributes into the Zed schema returned by Step 1.

**Constraints:**
- You MUST map `max_input_tokens` to `max_tokens`
- You MUST map `max_output_tokens` to `max_output_tokens`
- You MUST map `supports_function_calling` to `capabilities.tools`
- You MUST map `supports_vision` to `capabilities.images`
- You MUST include `capabilities.parallel_tool_calls` and `capabilities.prompt_cache_key` in every emitted entry, including when the derived value is `false`, because Eden AI expects requests to carry both fields and Zed only sends them when the capability is present
- You MUST derive `capabilities.parallel_tool_calls` from the catalog: mirror `supports_parallel_function_calling` when it is declared; when it is absent, inherit `supports_function_calling`, since a tool-capable chat model is expected to accept the parallel flag; use `false` when both are false or absent, and flag the value as inherited whenever the dedicated flag was missing
- You MUST derive `capabilities.prompt_cache_key` from the catalog: use `true` when `cache_read_input_token_cost` or one of its variants (for example `cache_read_input_token_cost_above_200k_tokens`) is present and greater than zero, and `false` when it is zero or absent, because those cost fields are the catalog's only signal that caching is supported and priced
- You MUST NOT hardcode either capability to `true` because enabling a flag the upstream model does not support can cause the provider to reject the request
- You MUST include `max_tokens` because Zed documents it as required, and a missing context window prevents the model from loading
- You MUST omit any other optional field whose source value is missing or `null` rather than substituting an estimate because wrong limits cause context truncation or provider-side errors
- You MUST use `model_id` verbatim as `name`, even when the catalog key carries a provider prefix or different separators
- You SHOULD derive `display_name` from the model family and version, preserving version numbers (for example `deepseek-v4.1-flash-1017` becomes `DeepSeek V4.1 Flash`)
- You MUST add a top-level `reasoning_effort` field set to the highest thinking level the model supports, selected in this order:
  1. If a matching entry declares `reasoning_effort_levels`, take the highest value in that array, ranked `none` < `minimal` < `low` < `medium` < `high` < `xhigh` < `max`
  2. When the vendor-native entry declares levels, use it; otherwise take the union of the level arrays across matching entries
  3. If no entry declares levels but `supports_reasoning` is `true`, emit `"high"` and flag it as inferred, since the boolean implies medium/high support without naming a ceiling
  4. If `supports_reasoning` is `false` or absent, omit `reasoning_effort` and flag that the model declares no reasoning support
- You MUST NOT select `"none"` as the maximum because Zed documents it as the value that disables thinking
- You MAY set `capabilities.max_tokens_parameter` to `true` when the target gateway expects the output limit as `max_tokens` instead of `max_completion_tokens`
- You SHOULD leave remaining capability flags at Zed's documented defaults unless the catalog provides explicit evidence to override them

### 5. Emit the Configuration Entry

Print the resulting JSON object.

**Constraints:**
- You MUST print a single JSON object suitable for insertion into `available_models`
- You MUST produce valid JSON with no trailing comma because the output is pasted directly into `settings.json`
- You MUST order the fields as `name`, `display_name`, `max_tokens`, `max_output_tokens`, `reasoning_effort`, `capabilities`
- You MUST keep `reasoning_effort` outside `capabilities` because Zed defines it as a model-level field
- You MUST print only the JSON inside its code fence so it can be copied without editing
- You MUST state outside the code fence which catalog key supplied the values and whether the match was exact
- You MUST flag every value that was derived, conservative, or unresolved, and You MUST state that values not found in the catalog were omitted rather than estimated

## Examples

### Example 1: Model ID Matches a Vendor-Native Key

**Input:**
- model_id: `kimi-k3`

**Expected Behavior:**
The agent finds `moonshot/kimi-k3` (vendor-native key, suffix match) with `max_input_tokens` 1048576, `max_output_tokens` 1048576, `supports_function_calling` true, `supports_vision` true, and `reasoning_effort_levels` `["low","high","max"]`, and prints:

```json
{
  "name": "kimi-k3",
  "display_name": "Kimi K3",
  "max_tokens": 1048576,
  "max_output_tokens": 1048576,
  "reasoning_effort": "max",
  "capabilities": {
    "tools": true,
    "images": true,
    "parallel_tool_calls": true,
    "prompt_cache_key": true
  }
}
```

The agent notes that the catalog key was `moonshot/kimi-k3`, resolved by suffix match, that `max` is the highest declared level, and that reseller entries report smaller output caps. It sets `parallel_tool_calls` to `true` by inheriting `supports_function_calling` because the dedicated flag is absent, and `prompt_cache_key` to `true` because `cache_read_input_token_cost` is 3E-7.

### Example 2: Model ID Requires Normalization and Providers Disagree

**Input:**
- model_id: `deepseek-v4.1-flash-1017`

**Expected Behavior:**
No exact key exists. The agent normalizes `.` to `p` and finds `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash-1017` (1048576 / 393216), `baseten/deepseek-ai/DeepSeek-V4.1-Flash-1017` (1048576 / 262144), and `deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017` (1048576 / 131072). It picks the conservative output cap and prints:

```json
{
  "name": "deepseek-v4.1-flash-1017",
  "display_name": "DeepSeek V4.1 Flash",
  "max_tokens": 1048576,
  "max_output_tokens": 131072,
  "reasoning_effort": "high",
  "capabilities": {
    "tools": true,
    "images": true,
    "parallel_tool_calls": true,
    "prompt_cache_key": true
  }
}
```

The agent states that the match was normalized rather than exact, lists the three provider entries and their output caps, and explains that the lowest cap was chosen because the routing provider behind Eden AI is unknown. It also flags that no candidate declares `reasoning_effort_levels` and that `"high"` was inferred from `supports_reasoning: true`. Both capability values are `true`: `supports_parallel_function_calling` is absent so `parallel_tool_calls` inherits `supports_function_calling`, and `cache_read_input_token_cost` is 4.2E-9 (non-zero) so `prompt_cache_key` is enabled.

### Example 3: Entry Absent From the Catalog

**Input:**
- model_id: `some-new-model-preview`

**Expected Behavior:**
The agent reports that no exact, normalized, or family match exists, lists the closest keys it found, and asks whether to proceed with user-supplied limits. It MUST NOT emit an entry with invented `max_tokens`, `max_output_tokens`, or `reasoning_effort`.

## Troubleshooting

### `zed.dev/llms.txt` Does Not Contain the Schema
The file is a site index. Follow its documentation link to `https://zed.dev/docs` and open `https://zed.dev/docs/ai/use-api-access`, section "OpenAI-Compatible Endpoints". If Zed has restructured its docs, search the docs index for "OpenAI-compatible" and report the new location.

### Model Not Found in the Catalog
Broaden the search progressively: suffix match, then case-insensitive match, then separator normalization (`.`/`-`/`p`), then family match without the snapshot suffix. If still absent, report the nearest candidates and stop. Do not guess limits.

### Several Providers Report Different Limits
This is expected, since the catalog records what each reseller supports. Prefer the vendor-native entry; when that is absent, choose the most conservative output cap and state the range so the user can raise it after observing what Eden AI routes to.

### All Fields Missing for an Entry
Some entries exist only for pricing and have `null` limits (for example entries under `perplexity/`). Treat them as unusable for this SOP and continue searching for a complete entry.

### Context Window Overflow While Inspecting the Catalog
The catalog is several megabytes. Ensure it is downloaded to disk and queried with `jq` or `grep`; never fetch it as document text and never print it wholesale.

### Parallel Tool Calling Not Declared
`supports_parallel_function_calling` is populated for only a few entries. When it is absent, inherit `supports_function_calling` and state that the value was inherited, because defaulting to `false` for every model that omits the flag would silently serialise tool use.

### Cache Cost Reported as Zero
A `cache_read_input_token_cost` of `0.0` means the catalog does not price cache reads for that entry, so set `prompt_cache_key` to `false` rather than assuming caching is free. Keep the field present with the `false` value.

### Reasoning Levels Not Declared
If no entry lists `reasoning_effort_levels`, apply the Step 4 fallback: emit `"high"` when `supports_reasoning` is true and state that it was inferred. Do not silently emit `"max"`, since an unsupported effort can be rejected by the upstream provider.

### Endpoint Rejects the Selected Effort
If Eden AI returns an error for `reasoning_effort`, lower it one step at a time (`max` to `xhigh` to `high` to `medium`) and report the value that worked, because gateways often expose fewer levels than the underlying model.

### Zed Rejects the Generated Entry
Check for a trailing comma, an unquoted key, or a field name the current Zed version does not define. Re-read the schema from Step 1 rather than removing fields arbitrarily.
