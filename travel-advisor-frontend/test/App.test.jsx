import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../src/App.jsx';

const question = { reply: 'How many days will you stay?', response_id: 'resp_one', status: 'needs_info', trip: null, budget_context: 'signed-context' };
const costs = { accommodation: 360, food: 180, transportation: 45, activities: 95, extras: 40 };
const ready = { reply: 'Rome discovery', response_id: 'resp_two', status: 'ready', budget_context: 'next-context',
  trip: { title: 'Rome Discovery', destination: 'Rome', duration_days: 1, interests: ['history'], summary: 'Your Roman escape.',
    days: [{ day_number: 1, morning: 'Explore the Colosseum', afternoon: 'Walk the Forum', evening: 'Dinner in Trastevere', places: ['Colosseum'], food_suggestion: 'Try carbonara' }],
    budget: { ...costs, flights: null, currency: 'EUR' }, practical_tips: ['Book museum tickets ahead.'] },
  budget_details: { costs, total: 720, flights_included: false, currency: 'EUR', sources: { accommodation: 'user_supplied', food: 'ai_estimate' } } };
const response = (data, ok = true) => Promise.resolve({ ok, json: async () => data });
beforeEach(() => { Element.prototype.scrollIntoView = vi.fn(); vi.stubGlobal('fetch', vi.fn()); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('Travel chat', () => {
  it('sends a suggestion, carries memory and signed budget context, and renders a full itinerary', async () => {
    const user = userEvent.setup();
    fetch.mockImplementationOnce(() => response(question)).mockImplementationOnce(() => response(ready));
    render(<App/>);
    await user.click(screen.getByRole('button', { name: 'Plan a 5-day trip to Japan' }));
    await screen.findByText(question.reply);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ message: 'Plan a 5-day trip to Japan' });
    await user.type(screen.getByRole('textbox'), 'Actually, Rome for 1 day. I like history.');
    await user.keyboard('{Enter}');
    await screen.findByRole('heading', { name: 'Rome Discovery' });
    const request = JSON.parse(fetch.mock.calls[1][1].body);
    expect(request.previous_response_id).toBe('resp_one');
    expect(request.budget_context).toBe('signed-context');
    for (const text of ['Explore the Colosseum', 'Walk the Forum', 'Dinner in Trastevere', 'Book museum tickets ahead.', 'User supplied · amount checked', '€720.00']) expect(screen.getByText(text)).toBeTruthy();
    expect(screen.getAllByText('AI estimate').length).toBeGreaterThan(0);
    expect(screen.getByText('Unknown')).toBeTruthy();
  });

  it('submits explicit costs and clears memory and budget on New Trip', async () => {
    const user = userEvent.setup();
    fetch.mockImplementation(() => response(question));
    render(<App/>);
    await user.click(screen.getByText('Add your costs'));
    await user.type(screen.getByLabelText('accommodation cost in EUR'), '360');
    await user.type(screen.getByRole('textbox'), 'Rome');
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText(question.reply);
    expect(JSON.parse(fetch.mock.calls[0][1].body).expected_budget).toEqual({ accommodation: 360 });
    await user.click(screen.getByRole('button', { name: 'New Trip' }));
    expect(screen.queryByText(question.reply)).toBeNull();
    expect(screen.getByLabelText('accommodation cost in EUR').value).toBe('');
    await user.click(screen.getByRole('button', { name: 'I want to explore Italy' }));
    await screen.findByText(question.reply);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ message: 'I want to explore Italy' });
  });

  it('blocks duplicate submissions and discards an old pending reply after reset', async () => {
    const user = userEvent.setup(); let resolve;
    fetch.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<App/>);
    await user.type(screen.getByRole('textbox'), 'Japan');
    await user.keyboard('{Enter}{Enter}');
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Send message' }).disabled).toBe(true);
    const signal = fetch.mock.calls[0][1].signal;
    await user.click(screen.getByRole('button', { name: 'New Trip' }));
    expect(signal.aborted).toBe(true);
    resolve(await response(question));
    await waitFor(() => expect(screen.queryByText(question.reply)).toBeNull());
    expect(screen.getByRole('button', { name: 'Plan a 5-day trip to Japan' })).toBeTruthy();
  });

  it('preserves failed messages for retry and supports Shift+Enter', async () => {
    const user = userEvent.setup();
    fetch.mockImplementationOnce(() => response({ error: 'No available credits.' }, false)).mockImplementationOnce(() => response(question));
    render(<App/>);
    const input = screen.getByRole('textbox');
    await user.type(input, 'Japan');
    await user.keyboard('{Shift>}{Enter}{/Shift}Food');
    expect(fetch).not.toHaveBeenCalled();
    expect(input.value).toBe('Japan\nFood');
    await user.keyboard('{Enter}');
    await screen.findByRole('alert');
    expect(input.value).toBe('Japan\nFood');
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText(question.reply);
    expect(JSON.parse(fetch.mock.calls[1][1].body).previous_response_id).toBeUndefined();
  });

  it('keeps legacy Markdown responses safe', async () => {
    const user = userEvent.setup();
    fetch.mockImplementation(() => response({ reply: '**Welcome** <script>danger()</script>', response_id: 'resp_legacy' }));
    const { container } = render(<App/>);
    await user.click(screen.getByRole('button', { name: 'I want to explore Italy' }));
    await screen.findByText('Welcome');
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('strong').textContent).toBe('Welcome');
  });
});
