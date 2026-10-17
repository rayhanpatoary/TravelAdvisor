// This file runs only on the server. Never import it from src/.
export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Please use POST to send a message.' });
  }
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { return res.status(400).json({ error: 'Invalid JSON request.' }); }
  }
  const { message, previous_response_id: previousId } = body || {};
  if (typeof message !== 'string' || !message.trim() || message.length > 8000 ||
      (previousId != null && (typeof previousId !== 'string' || !/^resp_[a-zA-Z0-9_-]{1,250}$/.test(previousId)))) {
    return res.status(400).json({ error: 'Enter a message of up to 8,000 characters with a valid conversation ID.' });
  }
  const token = process.env.TRAVEL_API_TOKEN;
  let backend;
  try {
    backend = new URL(process.env.TRAVEL_BACKEND_URL);
    if (backend.protocol !== 'https:' || backend.username || backend.password) throw new Error();
  } catch { return res.status(503).json({ error: 'The travel service is not configured. Please contact the site owner.' }); }
  if (!token) return res.status(503).json({ error: 'The travel service is not configured. Please contact the site owner.' });
  try {
    const upstream = await fetch(`${backend.href.replace(/\/$/, '')}/chat`, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(55000),
      headers: { 'Content-Type': 'application/json', 'X-API-Key': token },
      body: JSON.stringify({ message: message.trim(), ...(previousId ? { previous_response_id: previousId } : {}) }),
    });
    if (!upstream.ok) {
      const status = upstream.status;
      return res.status(status === 429 ? 429 : 502).json({ error:
        status === 401 || status === 403 ? 'The travel service could not authenticate. Please contact the site owner.' :
        status === 429 ? 'The travel service is busy. Please wait a moment and try again.' :
        'Your travel advisor is temporarily unavailable. Please try again shortly.' });
    }
    const data = await upstream.json();
    if (typeof data.reply !== 'string' || !data.reply.trim() || typeof data.response_id !== 'string' || !/^resp_[a-zA-Z0-9_-]{1,250}$/.test(data.response_id)) throw new Error();
    return res.status(200).json({ reply: data.reply, response_id: data.response_id });
  } catch (error) {
    const timedOut = error.name === 'TimeoutError' || error.name === 'AbortError';
    return res.status(timedOut ? 504 : 502).json({ error: timedOut ? 'Planning is taking longer than expected. Please try again.' : 'We could not reach your travel advisor. Please try again shortly.' });
  }
}
