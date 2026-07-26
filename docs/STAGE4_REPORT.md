# Stage 4 Report: OpenAI-Compatible LLM

Date: 2026-07-26

## Result

Stage 4 passed with a local OpenAI-compatible mock. No real API key was
available or used, so this report does not claim validation against a paid
external provider.

## Implementation

- Extended the existing `llm.py`; no API logic was added to the browser or
  `app.py`.
- Added `.env` configuration for provider, base URL, API key, model, timeout,
  retries, temperature, history limit, stream mode and system prompt.
- Uses the standard `POST /v1/chat/completions` API and
  `Authorization: Bearer`.
- Supports streaming and non-streaming responses.
- Keeps independent history per LiveTalking `sessionid`.
- Trims history to the configured maximum number of turns.
- Supports clearing, cancelling and removing a single session.
- Serializes generation requests per session.
- Removes Markdown syntax, fenced code and URLs before passing text to TTS.
- Emits safe SSE states for generating, answer, synthesizing, interrupted and
  error.
- Added:
  - `GET /api/chat/history`
  - `POST /api/chat/clear`
- Redacts keys/tokens/secrets from startup configuration logs and the admin
  configuration API.
- Added `scripts/mock_openai_server.py` for local integration testing.

## Automated Tests

Command:

```powershell
E:\SZR\.conda\envs\livetalking-local\python.exe -m unittest tests.test_llm_stage4 -v
```

Result: 13 tests passed. The full suite was run twice consecutively after the
test server connection lifecycle was corrected.

Covered:

- Streaming response
- Non-streaming response
- Multi-turn history
- Session isolation
- Maximum history length
- Clear one session without affecting another
- Markdown/code/URL speech cleanup
- Missing API key
- Invalid API key / HTTP 401
- Invalid model / HTTP 404
- Rate limiting / HTTP 429
- Timeout
- Unavailable service / invalid base URL
- Empty response
- Non-JSON response
- Interrupted stream
- Bearer authorization header

Regression:

- Stage 3 EdgeTTS tests: 8 passed.

## Security Boundary

- `.env.example` contains empty LLM credential fields only.
- The key is not returned by browser APIs.
- Logs record only session ID, safe error code and timing.
- Error responses never contain the API key or complete request headers.
- The bundled mock key is fixed test data and is not a real credential.

## Remaining External Validation

After the user configures a real provider in `.env`, that provider still needs
one live smoke test because individual OpenAI-compatible services can differ in
model names, rate limits and streaming behavior.
