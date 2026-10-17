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
  const { message, previous_response_id: previousId, expected_budget: budget, budget_context: context } = body || {};
  const budgetKeys = ['accommodation', 'food', 'transportation', 'activities', 'extras', 'flights'];
  const invalidBudget = budget != null && (typeof budget !== 'object' || Array.isArray(budget) ||
    Object.entries(budget).some(([key, value]) => !budgetKeys.includes(key) || typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 100000));
  if (typeof message !== 'string' || !message.trim() || message.length > 8000 ||
      invalidBudget || (context != null && (typeof context !== 'string' || context.length > 5000)) ||
      (previousId != null && (typeof previousId !== 'string' || !/^resp_[a-zA-Z0-9_-]{1,250}$/.test(previousId)))) {
    return res.status(400).json({ error: 'Enter a message of up to 8,000 characters with a valid conversation ID.' });
  }
  const token = process.env.TRAVEL_API_TOKEN;
  let backend;
  try {
    backend = new URL(process.env.TRAVEL_BACKEND_URL);
    const localDevelopment = process.env.NODE_ENV !== 'production' && !process.env.VERCEL &&
      backend.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(backend.hostname);
    if ((!localDevelopment && backend.protocol !== 'https:') || backend.username || backend.password || backend.search || backend.hash) throw new Error();
  } catch { return res.status(503).json({ error: 'The travel service is not configured. Please contact the site owner.' }); }
  if (!token) return res.status(503).json({ error: 'The travel service is not configured. Please contact the site owner.' });
  try {
    const upstream = await fetch(`${backend.href.replace(/\/$/, '')}/chat`, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(55000),
      headers: { 'Content-Type': 'application/json', 'X-API-Key': token },
      body: JSON.stringify({ message: message.trim(), ...(previousId ? { previous_response_id: previousId } : {}),
        ...(budget ? { expected_budget: budget } : {}), ...(context ? { budget_context: context } : {}) }),
    });
    if (!upstream.ok) {
      const status = upstream.status;
      let code;
      try { code = (await upstream.json()).code; } catch { /* Non-JSON Vercel errors stay generic. */ }
      if (code === 'quota_exhausted') return res.status(429).json({ error: 'The AI service has no available credits. The site owner needs to check billing.' });
      if (code === 'invalid_duration') return res.status(422).json({ error: 'Please plan a trip segment between 1 and 30 days.' });
      if (status === 422) return res.status(422).json({ error: 'Check your whole-trip EUR costs and matching budget values. If the conversation expired, start a new trip.' });
      if (status === 400) return res.status(400).json({ error: 'This conversation could not be continued. Please start a new trip.' });
      return res.status([429, 503, 504].includes(status) ? status : 502).json({ error:
        status === 401 || status === 403 ? 'The travel service could not authenticate. Please contact the site owner.' :
        status === 429 ? 'The travel service is busy. Please wait a moment and try again.' :
        'Your travel advisor is temporarily unavailable. Please try again shortly.' });
    }
    const data = await upstream.json();
    if (typeof data.reply !== 'string' || !data.reply.trim() || typeof data.response_id !== 'string' || !/^resp_[a-zA-Z0-9_-]{1,250}$/.test(data.response_id)) throw new Error();
    const result = { reply: data.reply, response_id: data.response_id };
    if (['ready', 'needs_info'].includes(data.status)) {
      if (data.status === 'ready' && (!data.trip || !Array.isArray(data.trip.days))) throw new Error();
      result.status = data.status;
      result.trip = data.trip ?? null;
      result.budget_details = data.budget_details ?? null;
      if (['none', 'calculate_trip_budget', 'suggest_activities'].includes(data.tool_used)) result.tool_used = data.tool_used;
    }
    if (typeof data.budget_context === 'string' && data.budget_context.length <= 5000) result.budget_context = data.budget_context;
    return res.status(200).json(result);
  } catch (error) {
    const timedOut = error.name === 'TimeoutError' || error.name === 'AbortError';
    return res.status(timedOut ? 504 : 502).json({ error: timedOut ? 'Planning is taking longer than expected. Please try again.' : 'We could not reach your travel advisor. Please try again shortly.' });
  }
}
