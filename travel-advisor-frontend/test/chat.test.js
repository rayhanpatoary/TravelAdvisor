import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import handler from '../api/chat.js';

const originalFetch = globalThis.fetch;
const originalEnv = { token: process.env.TRAVEL_API_TOKEN, url: process.env.TRAVEL_BACKEND_URL };
afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const [key, value] of [['TRAVEL_API_TOKEN', originalEnv.token], ['TRAVEL_BACKEND_URL', originalEnv.url]]) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  }
});
async function invoke(body, method = 'POST') {
  const res = { headers: {}, setHeader(key, value) { this.headers[key] = value; }, status(code) { this.code = code; return this; }, json(value) { this.body = value; return this; } };
  await handler({ method, body }, res);
  return res;
}
function configure() { process.env.TRAVEL_API_TOKEN = 'private-test-token'; process.env.TRAVEL_BACKEND_URL = 'https://backend.example'; }
test('rejects methods and invalid input before contacting upstream', async () => {
  globalThis.fetch = () => { throw new Error('must not fetch'); };
  assert.equal((await invoke({}, 'GET')).code, 405);
  for (const body of ['{', {}, { message: ' ' }, { message: 'x'.repeat(8001) }, { message: 'Hello', previous_response_id: {} }]) assert.equal((await invoke(body)).code, 400);
});
test('forwards the private header and conversation contract, returning only public fields', async () => {
  configure();
  const calls = [];
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ reply: 'Where in Japan?', response_id: 'resp_next', secret: 'hidden' }) }; };
  const first = await invoke({ message: ' Japan ' });
  assert.deepEqual(first.body, { reply: 'Where in Japan?', response_id: 'resp_next' });
  assert.deepEqual(JSON.parse(calls[0].options.body), { message: 'Japan' });
  await invoke({ message: 'Tokyo', previous_response_id: 'resp_next' });
  assert.equal(calls[1].url, 'https://backend.example/chat');
  assert.equal(calls[1].options.headers['X-API-Key'], 'private-test-token');
  assert.equal(JSON.parse(calls[1].options.body).previous_response_id, 'resp_next');
  assert.equal(first.headers['Cache-Control'], 'no-store');
});
test('does not expose upstream errors or authentication details', async () => {
  configure();
  for (const status of [401, 403, 429, 500]) {
    globalThis.fetch = async () => ({ ok: false, status, json: async () => ({ detail: 'private-test-token' }) });
    const result = await invoke({ message: 'Hello' });
    assert.equal(result.code, status === 429 ? 429 : 502);
    assert.ok(!JSON.stringify(result.body).includes('private-test-token'));
  }
});
test('handles missing config, malformed upstream replies, network failures and timeouts', async () => {
  configure(); delete process.env.TRAVEL_API_TOKEN;
  assert.equal((await invoke({ message: 'Hello' })).code, 503);
  configure();
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ reply: 'Hello' }) });
  assert.equal((await invoke({ message: 'Hello' })).code, 502);
  globalThis.fetch = async () => { throw new TypeError('secret network details'); };
  assert.equal((await invoke({ message: 'Hello' })).code, 502);
  globalThis.fetch = async () => { throw new DOMException('timeout', 'TimeoutError'); };
  assert.equal((await invoke({ message: 'Hello' })).code, 504);
});
