# AI Travel Advisor

A responsive React chat app for planning personalized trips with the existing FastAPI backend. Includes suggested destinations, safe Markdown itineraries, conversation memory, loading and error states, and a New Trip reset.

## Stack and structure

JavaScript, React Hooks, Vite, plain CSS, Lucide icons, Fetch, and react-markdown (raw HTML is disabled).

```text
api/chat.js              Server-side Vercel proxy
server/dev.js            Local server: Vite + the same API handler
src/App.jsx              Chat state, requests, conversation memory
src/components/          Header, ChatMessage, ChatInput
src/App.css              Responsive layout and styling
src/index.css            Base styles
src/main.jsx             React entry point
test/chat.test.js        Proxy contract and failure checks
vercel.json              Function timeout and SPA routing
```

## Run locally

Use Node.js 22.9+ (Node 24 recommended) and npm.

```sh
cd travel-advisor-frontend
npm install
```

Copy `.env.example` to `.env.local` and replace the placeholder token with the **same TRAVEL_API_TOKEN configured on your backend**:

```dotenv
TRAVEL_API_TOKEN=your-private-backend-token
TRAVEL_BACKEND_URL=https://travel-advisor-api-beta.vercel.app
```

Do not commit this file. Never use a `VITE_` variable for the token: Vite makes those available to the browser.

```sh
npm run dev
```

Open http://127.0.0.1:5173. This command runs React and `/api/chat` together, without needing a Vercel account. The server reads `.env.local` for each chat request, so local file changes take effect without a restart. `.env.example` is only a template; editing it does not configure the server. `npm run dev:ui` runs only Vite, without the API proxy.

Alternatively, install the Vercel CLI and run `vercel dev` in this directory to use Vercel's local runtime. Select the Vite framework if prompted; use `npm run dev:ui` as the development command (not `npm run dev`, which already runs its own proxy). Configure the same server environment variables locally or pull them with `vercel env pull .env.local` after linking your project. The CLI may require sign-in.

## How requests work

The browser posts to its own `/api/chat`. The server validates the request, adds the private `X-API-Key` header, and forwards it to `TRAVEL_BACKEND_URL/chat`. Only `reply` and `response_id` are returned. Upstream error bodies and tokens are never returned or logged by this proxy. HTTPS is required for the backend URL.

The initial request contains `{ "message": "I want to travel to Japan" }`. React stores the returned `response_id` in memory and sends it as `previous_response_id` on the next successful turn. New Trip clears that ID and messages and cancels any pending browser request. Refreshing also starts a fresh conversation. Conversation history is not saved in browser storage.

Failures restore the unsent message to the input so you can retry. Network failures, upstream authentication failures, rate limits, timeouts, and invalid responses have friendly error states. Failed requests do not advance the stored conversation ID. If a request finishes upstream after a connection failure, retrying can still incur another upstream request.

## Verify

```sh
npm test
npm run build
```

`npm run preview` previews the static production build only; use the full local server or `vercel dev` for chat.

To check the real integration with a configured token:

1. Start `npm run dev` and send “Plan a 5-day trip to Japan”.
2. Reply with your interests and confirm the advisor remembers Japan and five days.
3. Check browser Network: requests go to `/api/chat` and contain no private API key.
4. Select New Trip and confirm the next request omits `previous_response_id`.
5. Test a narrow mobile viewport, Enter to send, and Shift+Enter for a new line.

Automated proxy tests mock the upstream service and do not prove live OpenAI connectivity.

## Deploy a separate Vercel project

1. Import the same GitHub repository as a **new** Vercel project.
2. Set Root Directory to `travel-advisor-frontend` and framework to Vite.
3. Build command: `npm run build`. Output directory: `dist`. Install command: `npm install`.
4. Set `TRAVEL_API_TOKEN` and `TRAVEL_BACKEND_URL` in Vercel project environment variables for the environments you use (Production and optionally Preview/Development).
5. Deploy when ready. Redeploy after changing production variables.

`api/chat.js` becomes a Node serverless function; `vercel.json` preserves filesystem/API routing before the SPA fallback. No backend CORS changes are needed because the browser calls the frontend origin and the proxy contacts FastAPI from the server.

The proxy is public: keeping the backend key private does **not** prevent people from using the proxy. Before broad public use, add user authentication and/or durable rate limiting (for example Vercel Firewall or a shared rate-limit store), plus usage limits and monitoring to control API costs. An in-memory limiter is unreliable across serverless instances. The app itself does not implement these controls.

Travel guidance can be inaccurate; verify prices, entry requirements, and availability before booking. Fonts load from Google Fonts with local sans-serif fallbacks.
