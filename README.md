# AI Travel Advisor

Conversational trip planning with a React frontend, a private Node proxy, and a FastAPI/OpenAI backend. The existing notebook is preserved as the experimental reference; deployed apps import Python modules, not notebook cells.

## Architecture

```text
Browser (React, Vite)
  → same-origin POST /api/chat (Node server-side proxy)
    → POST /chat (FastAPI, private X-API-Key)
      → OpenAI Responses API, gpt-4.1-mini
      ↔ validated Python budget and activity tools
```

The frontend project and backend project deploy separately. API keys never enter React, browser headers, or `VITE_` variables. The browser sees an opaque signed budget context containing costs and a conversation ID, never the signing secret.

## What changed

| Feature | Original FastAPI | Notebook/teammate contribution | Application integration |
| --- | --- | --- | --- |
| Conversation and memory | Plain text, `previous_response_id` | Original instructions and conversational loop | Retained; instructions resent on every API call |
| Structured itinerary | None | `DayPlan`, `TripBudget`, `TripPlan`, `TravelResponse` and `responses.parse` examples | Pydantic structured output, status checks, sequential day validation, rendered cards |
| Budget | AI prose | Five-category calculator, `BudgetToolInput`, argument verification | Python arithmetic, optional flights, explicit user costs versus estimates, signed provenance across turns |
| Activities | AI prose | Rome/Paris history/food/culture database and function schema | Preserved database, safe empty-result fallback for other places/interests |
| Tools | None | Selection → validation → execution → function output → final response | Allowlist, bounded workflow, multiple call handling, safe errors |
| Security checks | Private backend token | Negative-cost and injected-argument examples | Runtime validation, deterministic cost comparison, regression tests, no raw error/secret logging |
| Errors | Unhandled OpenAI exceptions produced HTTP 500 | Engine returned error dictionaries | Safe non-2xx JSON, distinct credit exhaustion and rate limits, SDK retries disabled |

`prompts.py` was empty in the supplied supporting files; it now centralizes the original conversational behavior and the teammate's tool/security rules. The original `answer` field remains an alias for notebook callers; HTTP clients continue to receive `reply` and `response_id`.

## Files

```text
main.ipynb                        Merged reference, unchanged
travel-advisor-api/
  app.py                         Auth, input validation, error mapping, API entry point
  prompts.py                     Conversation and tool instructions
  schemas.py                     Shared Pydantic schemas
  tools.py                       Budget calculator and preserved activity database
  travel_engine.py               OpenAI structured response and tool workflow
  budget_context.py              Signed, expiring context and labelled-cost parsing
  tests/                         Mocked pytest coverage
  requirements.txt               Runtime dependencies
  requirements-dev.txt           Test dependencies
  vercel.json                    Function duration
travel-advisor-frontend/
  api/chat.js                    Private proxy and safe error translation
  server/dev.js                  Local Vite + proxy server
  src/components/TripItinerary.jsx Structured days, tips, budget and provenance
  src/components/BudgetInput.jsx Explicit optional EUR costs
  test/                          Proxy and React interaction tests
```

## Run locally (PowerShell)

From the repository root, using Python 3.12 and Node 22.9+ (Node 24 recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r travel-advisor-api/requirements-dev.txt
Copy-Item travel-advisor-api/.env.example travel-advisor-api/.env
```

If `.env` already exists, edit it instead of overwriting it. Set these **server-only** backend values:

```dotenv
OPENAI_API_KEY=your-real-openai-key
TRAVEL_API_TOKEN=your-private-backend-token
```

The backend loads its own `.env` and falls back to the repository `.env`; process environment takes precedence. OpenAI key configuration is checked at request time rather than crashing the app at import. A valid key also needs API credits and access to `gpt-4.1-mini`.

Run the backend:

```powershell
cd travel-advisor-api
..\.venv\Scripts\python.exe -m uvicorn app:app --reload --port 8000
```

In a second terminal:

```powershell
cd travel-advisor-frontend
npm install
Copy-Item .env.example .env.local
```

Preserve an existing `.env.local`. Set:

```dotenv
TRAVEL_API_TOKEN=the-same-private-backend-token
TRAVEL_BACKEND_URL=http://127.0.0.1:8000
```

```powershell
npm run dev
```

Open http://127.0.0.1:5173. HTTP backend URLs are allowed only for loopback local development; Vercel/production requires HTTPS. Use `https://travel-advisor-api-beta.vercel.app` to contact the deployed backend after its updated code has been deployed. Local code changes do not update that deployment.

`npm run dev` runs the React app and proxy. The server reloads `.env.local` per request. `.env.example` is only a template. The Vite-only `npm run dev:ui` and static `npm run preview` do not provide a chat proxy. You can also use `vercel dev`, with Vite's `npm run dev:ui` as the development command and the same server environment variables.

## API and conversation memory

Send `POST /chat` with `Content-Type: application/json` and `X-API-Key` in Postman or another server client. Browser clients use `/api/chat` without any private header.

```json
{
  "message": "I want to visit Rome for 3 days. I like history and food.",
  "previous_response_id": null,
  "expected_budget": { "accommodation": 360, "food": 180 }
}
```

Response always includes `reply` and `response_id` on success, and may include:

```json
{
  "reply": "How many days will you stay?",
  "response_id": "resp_example",
  "status": "needs_info",
  "trip": null,
  "tool_used": "none",
  "budget_details": null,
  "budget_context": "opaque-signed-context"
}
```

On the next request send the last successful `response_id` as `previous_response_id`, and the last `budget_context` unchanged. The latter preserves authoritative costs and explicit numeric duration for verification. Context expires after 24 hours and is bound to its response ID; New Trip resets both. Tokens are not authorization or cross-user isolation: a public app still needs user authentication, ownership checks for conversation IDs, and durable rate limiting before broad public use.

Old clients may omit new fields and continue conversational memory with `previous_response_id`. **Verified historical cost tracking requires returning the signed context**; legacy clients should resubmit explicit known costs on each request. React already returns the context automatically. Chat state is in browser memory only, so refresh starts a new trip. An aborted browser request can still finish upstream and consume credits.

## Structured responses and tools

Each model request uses the SDK's `responses.parse(..., text_format=TravelResponse)`. `needs_info` requires one follow-up question and no trip. `ready` requires a complete trip and no question. Pydantic rejects inconsistent states, nonsequential or mismatched days, empty required content, extra fields, invalid currency, negative/nonfinite amounts, and values above the per-category cap of EUR 100,000. Plans support 1–30 days. Explicit numeric durations such as `3 days` or `5-day` are checked against the generated itinerary and carried in signed context; arbitrary natural-language interpretation still depends on the model.

The model may request `calculate_trip_budget` or `suggest_activities`. Python parses JSON and validates typed arguments before executing the allowlisted pure functions. Each tool output goes back with its `call_id` as `function_call_output`. The final structured call disables more tools. At most two OpenAI requests and four tool calls are permitted per turn; duplicate call IDs, unknown functions, invalid arguments, incomplete output and repeated calls fail safely. There are no automatic SDK retries, including for exhausted quota.

Every ready itinerary's total is calculated in Python even when the model did not explicitly select the budget tool. The budget uses decimal arithmetic and rounds the total to cents. Five whole-trip categories plus known flights are included; unknown flights are excluded and clearly marked. Currency is EUR; the app does not perform exchange-rate conversions.

Use the optional budget form for known amounts, or unambiguous labelled whole-trip syntax such as `Accommodation: 360 EUR`. The authoritative figures are supplied separately from model arguments and compared before tool execution and before returning a ready itinerary. Repeated conflicting labelled costs are rejected; ambiguous natural-language costs or daily rates should be entered in the form. Historical costs persist via signed context. Enter a replacement amount in the form to change one; New Trip clears all saved amounts. Clearing a form field alone does not erase a previously saved cost. Other amounts are explicitly labelled AI estimates. “User supplied · amount checked” means matching the user's input, not verification with a vendor or booking service.

The Rome/Paris database is unchanged. Unsupported cities or interests return empty results with a fallback indicator; the AI can then suggest activities from general knowledge without pretending they came from the database. No booking, live pricing or web search tools are connected.

## Prompt injection defenses and limitations

System rules separate user/external text from instructions. Enforcement comes from the Python function allowlist, strict schemas, deterministic cost comparisons, server-calculated totals, signed context, and tests using malicious model arguments and copied-content attacks. No arbitrary code or unapproved tools execute. Prompts alone cannot guarantee correct behavior, detect every attack, or reliably distinguish all free-form prices from copied website text. Use explicit cost fields for reliable verification. Content quality, destination interpretation, the model asking exactly one question, and advice accuracy remain model-dependent. User text and model output are rendered as text/safe Markdown, without raw HTML.

## Errors and troubleshooting

Failures return safe JSON with `error` and a stable `code`, never as successful plans:

| Status | Meaning |
| --- | --- |
| 400 | OpenAI rejected the request or conversation; start New Trip |
| 401 | Missing or wrong backend `X-API-Key` |
| 422 | Invalid message, costs, conflicting values, or expired/tampered budget context |
| 429 + `quota_exhausted` | OpenAI credit/billing problem; the owner must fix billing |
| 429 + `rate_limited` | Temporary OpenAI rate limit; wait before manually retrying |
| 502 | Connection failure, invalid tool/model result, or other upstream error |
| 503 | Missing server settings or invalid OpenAI credentials |
| 504 | AI timeout |

The proxy preserves safe status distinctions and translates upstream responses without exposing raw bodies. Verify environment variables in the correct Vercel project/environment and redeploy after changes. A configured token alone cannot fix exhausted OpenAI credits. Never paste keys into logs or chat. Browser Network should show only same-origin requests, no `X-API-Key`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest travel-advisor-api/tests -q
cd travel-advisor-frontend
npm test
npm run build
```

Backend tests mock OpenAI, including one test that runs the real SDK parser over an HTTP mock. They cover schemas, arithmetic, flights, provenance, signed memory, activity fallbacks, tool selection/output, malicious arguments, invalid responses, authentication, quota and rate-limit handling. React tests use Vitest/jsdom and Testing Library to check conversation memory, structured rendering, budgets, New Trip, duplicate prevention, stale replies, retry, keyboard input and safe legacy Markdown. Proxy tests check server forwarding, redaction, validation and backwards compatibility. They consume no API credits and do not prove live provider connectivity.

For a manual Postman check, send the request above, then return its IDs/context with a follow-up. Inspect the structured day count and budget. Try a wrong API key (401), negative cost (422), and New Trip. A full live check requires available OpenAI credits and deployment of this backend version.

## Vercel deployment preparation

Reuse the **two existing projects**; do not create duplicates.

| Setting | Backend project | Frontend project |
| --- | --- | --- |
| Root Directory | `travel-advisor-api` | `travel-advisor-frontend` |
| Framework | FastAPI (automatic `app.py` detection) | Vite |
| Build / output | Leave defaults; no custom static output | `npm run build` / `dist` |
| Variables | `OPENAI_API_KEY`, `TRAVEL_API_TOKEN` | `TRAVEL_BACKEND_URL`, `TRAVEL_API_TOKEN` |

Select Python 3.12 for backend and Node 24 for frontend. Backend dependencies are entirely inside its project directory. `vercel.json` requests 60 seconds per function; OpenAI uses 24-second SDK timeouts, at most twice, and the frontend proxy has a 55-second upstream timeout. Runtime scheduling/network conditions can still trigger a timeout. Frontend filesystem routing preserves `/api/chat` before the SPA fallback. Production backend URLs require HTTPS.

After approval, update the existing backend deployment first, then the frontend. Environment variable changes require redeployment. Check preview/production variables separately and make sure the shared token matches. Validate authentication, missing-info replies, ready itineraries and follow-up memory after deployment. Add durable rate limiting/user auth and spending limits before broad public use.

Implementation reference: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), and [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

No deployment or Git push is part of the local implementation. Local tests and a successful build establish code readiness, not a completed cloud deployment or a live-credit check.
