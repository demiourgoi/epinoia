# Research: the OpenAI chat completions wire format

Sources:

- OpenAI API reference (chat completions): 
  https://platform.openai.com/docs/api-reference/chat
- Practitioner walkthrough of building an OpenAI-compatible API: 
  https://towardsdatascience.com/how-to-build-an-openai-compatible-api-87c8edea2f06/

## Findings

Non-streaming request (`POST /v1/chat/completions`):

```json
{
  "model": "string, required",
  "messages": [
    {"role": "system|user|assistant|tool", "content": "string or parts"},
    ...
  ],
  "stream": false,
  "temperature": 0.7, "top_p": 1.0, "max_tokens": 1024,
  "tools": [...], "tool_choice": "auto", ...
}
```

Non-streaming response:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1767075000,
  "model": "<echoed model>",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop|length|content_filter|tool_calls"
    }
  ],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

Streaming response: SSE on the same endpoint with `Content-Type:
text/event-stream`; each `data:` line carries a `chat.completion.chunk`
object whose `choices[].delta` accumulates `{"role": "assistant"}` then
`{"content": "..."}` deltas; the stream terminates with `data: [DONE]`.

Error format:

```json
{
  "error": {
    "message": "...",
    "type": "invalid_request_error|permission_error|api_error",
    "param": null,
    "code": null
  }
}
```

Client compatibility nuances:

- Clients validate `object`, `choices[].message.role`, `finish_reason`, and
  `id`; `usage` should be present (zeros are accepted when unknown).
- Requests commonly include sampling fields the agent cannot honor
  (`temperature`, `top_p`, ...); a compatible server accepts and ignores
  them.
- Chat roles beyond plain text (tool calls, function calling, image parts)
  have no mapping to a tools-disabled agent request; the proxy rejects
  `tools`/`tool_choice` (and tool-role messages without content) with an
  `invalid_request_error` rather than silently misrouting them.

## Consequence for azathoth

One pydantic request model validates the OpenAI payload; one response
builder emits exact OpenAI shapes for both modes, including SSE. The
`finish_reason` mapping is `end_turn -> stop`, `max_tokens -> length`,
`refusal -> content_filter`, other stop reasons -> `stop`.
