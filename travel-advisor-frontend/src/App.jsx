import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Compass, MapPin, Sparkles, Route, Heart, AlertCircle } from 'lucide-react';
import Header from './components/Header.jsx';
import ChatInput from './components/ChatInput.jsx';
import ChatMessage from './components/ChatMessage.jsx';
import BudgetInput from './components/BudgetInput.jsx';
import './App.css';

const welcome = { role: 'assistant', content: 'Hi there! I’m your AI travel advisor. Tell me where you’d like to go, and we’ll build a trip around what you love.' };
const prompts = [
  { place: 'Japan', detail: 'Culture, cuisine & a little adventure', prompt: 'Plan a 5-day trip to Japan', icon: '⛩', style: 'japan' },
  { place: 'Italy', detail: 'Slow days & unforgettable flavors', prompt: 'I want to explore Italy', icon: '🍋', style: 'italy' },
  { place: 'Paris', detail: 'A weekend with a certain je ne sais quoi', prompt: 'Suggest a weekend trip to Paris', icon: '☕', style: 'paris' },
];
export default function App() {
  const [messages, setMessages] = useState([welcome]);
  const [input, setInput] = useState('');
  const [responseId, setResponseId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [budgetValues, setBudgetValues] = useState({});
  const [budgetContext, setBudgetContext] = useState(null);
  const activeRequest = useRef(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const started = messages.length > 1;
  useEffect(() => { if (started) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, loading, error, started]);
  useEffect(() => () => activeRequest.current?.abort(), []);
  function newTrip() {
    activeRequest.current?.abort(); activeRequest.current = null;
    setMessages([welcome]); setResponseId(null); setInput(''); setError(''); setLoading(false);
    setBudgetValues({}); setBudgetContext(null);
    inputRef.current?.focus();
  }
  async function sendMessage(text = input) {
    if (activeRequest.current || !text.trim()) return;
    const expectedBudget = Object.fromEntries(Object.entries(budgetValues).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)]));
    if (Object.values(expectedBudget).some((value) => !Number.isFinite(value) || value < 0 || value > 100000)) {
      setError('Enter whole-trip EUR costs between 0 and 100,000.'); return;
    }
    const message = text.trim();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true); setError(''); setInput('');
    setMessages((current) => [...current, { role: 'user', content: message }]);
    try {
      const result = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ message, ...(responseId ? { previous_response_id: responseId } : {}),
          ...(Object.keys(expectedBudget).length ? { expected_budget: expectedBudget } : {}),
          ...(budgetContext ? { budget_context: budgetContext } : {}) }) });
      const data = await result.json();
      if (!result.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
      if (typeof data.reply !== 'string' || typeof data.response_id !== 'string') throw new Error('We received an unexpected reply. Please try again.');
      if (activeRequest.current !== controller) return;
      setMessages((current) => [...current, { role: 'assistant', content: data.reply,
        trip: data.status === 'ready' ? data.trip : null, budgetDetails: data.budget_details }]); setResponseId(data.response_id);
      setBudgetContext(data.budget_context || null);
    } catch (failure) {
      if (controller.signal.aborted || activeRequest.current !== controller) return;
      setError(failure instanceof TypeError ? 'Connection lost. Check your internet connection and try again.' : failure instanceof SyntaxError ? 'The travel service is unavailable. Please try again.' : failure.message);
      setInput(message);
      setMessages((current) => current.slice(0, -1));
    } finally {
      if (activeRequest.current === controller) { activeRequest.current = null; setLoading(false); inputRef.current?.focus(); }
    }
  }
  return <div className="app"><Header onNewTrip={newTrip}/><main>
    <section className="intro"><span className="eyebrow"><span className="status-dot"/> YOUR NEXT CHAPTER STARTS HERE</span><h1>A world of possibilities.<br/><em>A trip that’s yours.</em></h1><p>Big adventures or little escapes. Let’s turn your travel<br className="desktop-break"/> daydreams into a plan you’ll love.</p></section>
    <section className="workspace" aria-label="Trip planner"><div className="chat-panel"><div className="chat-heading"><span className="advisor-icon"><Compass size={22}/></span><div><h2>Your personal travel advisor</h2><span>Inspired by you. Planned together.</span></div><span className="ai-badge"><Sparkles size={12}/> AI-powered</span></div>
    <div className="conversation" role="log" aria-label="Travel conversation" aria-live="polite" aria-busy={loading}>{messages.map((message, index) => <ChatMessage key={index} message={message}/>)}
    {!started && <div className="suggestions"><p>A little inspiration to get you going</p><div className="prompt-grid">{prompts.map((item) => <button key={item.place} className={`prompt-card ${item.style}`} onClick={() => sendMessage(item.prompt)} disabled={loading} aria-label={item.prompt}><span className="destination-art" aria-hidden="true">{item.icon}<span className="art-orbit"/></span><span className="destination-title">{item.place}<ArrowUpRight size={16}/></span><span className="destination-detail">{item.detail}</span><span className="prompt-text">{item.prompt}</span></button>)}</div></div>}
    {loading && <div className="thinking"><span/><span/><span/> Planning a little possibility…</div>}<div ref={endRef}/></div>
    {error && <div role="alert" className="error"><AlertCircle size={17}/>{error} Your message is ready to resend.</div>}
    <BudgetInput values={budgetValues} onChange={(key, value) => setBudgetValues((current) => ({ ...current, [key]: value }))} disabled={loading}/>
    <ChatInput value={input} onChange={setInput} onSend={sendMessage} loading={loading} inputRef={inputRef}/><p className="disclaimer">A little AI inspiration, a lot of possibility. Always double-check travel details.</p></div>
    <aside><span className="aside-label">LESS SEARCHING. MORE DISCOVERING.</span><h2>Good trips start<br/>with a conversation.</h2><p>Consider this your blank map.<br/>We’ll fill in the good stuff together.</p><div className="benefit"><span><MapPin size={20}/></span><div><h3>Your kind of places</h3><p>Hidden gems and must-sees,<br/>matched to your interests.</p></div></div><div className="benefit"><span><Route size={20}/></span><div><h3>A plan that flows</h3><p>Thoughtful day-by-day itineraries<br/>with room to wander.</p></div></div><div className="benefit"><span><Heart size={20}/></span><div><h3>Made for you</h3><p>Your pace, your budget,<br/>your idea of a great trip.</p></div></div><div className="travel-note"><Sparkles size={18}/><p>Start with a place. Or a feeling.<br/><strong>We’ll take it from there.</strong></p></div></aside></section>
    <footer><Compass size={14}/> A little curiosity goes a long way.<span>MADE FOR YOUR NEXT ADVENTURE</span></footer>
  </main></div>;
}
