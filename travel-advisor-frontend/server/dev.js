import http from 'node:http';
import { createServer, loadEnv } from 'vite';
import { fileURLToPath } from 'node:url';
import handler from '../api/chat.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const settingNames = ['TRAVEL_API_TOKEN', 'TRAVEL_BACKEND_URL'];
const inheritedSettings = Object.fromEntries(settingNames.map((name) => [name, process.env[name]]));
// Read server settings per request so editing .env.local doesn't require a restart.
// Only these two settings are used, and neither is exposed through VITE_ variables.
function refreshServerSettings() {
  // Vite gives process.env priority: remove values assigned by our previous reload.
  for (const name of settingNames) {
    if (inheritedSettings[name] === undefined) delete process.env[name];
    else process.env[name] = inheritedSettings[name];
  }
  const settings = loadEnv('development', root, 'TRAVEL_');
  for (const name of settingNames) {
    if (settings[name] !== undefined) process.env[name] = settings[name];
    else delete process.env[name];
  }
}

// Vite middleware and the same Vercel handler share one local origin.
const vite = await createServer({ server: { middlewareMode: true }, appType: 'spa' });
const server = http.createServer(async (req, res) => {
  if (req.url?.split('?')[0] !== '/api/chat') return vite.middlewares(req, res);
  res.status = (code) => { res.statusCode = code; return res; };
  res.json = (value) => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(value)); };
  const chunks = [];
  let size = 0;
  try {
    for await (const chunk of req) {
      size += chunk.length;
      if (size > 40000) { res.status(413).json({ error: 'Message is too large.' }); return; }
      chunks.push(chunk);
    }
    req.body = Buffer.concat(chunks).toString();
    refreshServerSettings();
    await handler(req, res);
  } catch { if (!res.writableEnded) res.status(400).json({ error: 'Could not read the request.' }); }
});
server.listen(5173, '127.0.0.1', () => console.log('AI Travel Advisor: http://127.0.0.1:5173'));
