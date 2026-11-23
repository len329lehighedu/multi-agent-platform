const $ = (selector) => document.querySelector(selector);
const SVG = 'http://www.w3.org/2000/svg';
const STAGES = ['intake', 'planning', 'architecture', 'building', 'qa', 'review'];
const EXAMPLE = 'Build a module where learners fit a SINDy model to noisy pendulum data, test it on held-out data, and predict future motion.';
const SPECIALISTS = [
  { id: 'learning_planner', name: 'Learning Planner', role: 'Audience, objective, interaction' },
  { id: 'scientific_architect', name: 'Scientific Architect', role: 'Method, data, verification' },
  { id: 'builder', name: 'Module Builder', role: 'Build plan (no code yet)' },
  { id: 'qa_reviewer', name: 'QA Reviewer', role: 'Independent checks' },
];
const NAMES = { orchestrator: 'Orchestrator', ...Object.fromEntries(SPECIALISTS.map((a) => [a.id, a.name])) };
const LABELS = { idle: 'Idle', running: 'Working', waiting: 'Needs you', done: 'Done', failed: 'Failed' };

const state = { runId: null, cursor: 0, phase: 'idle', source: null, shown: new Set(), queue: Promise.resolve(), nodes: {}, edges: {} };

function svg(tag, attrs = {}, parent) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (parent) parent.append(node);
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || 'Request failed');
  return body;
}

/* ---------- graph ---------- */
function buildGraph() {
  const graph = $('#graph');
  graph.replaceChildren();
  state.nodes = {};
  state.edges = {};
  const hub = { x: 30, y: 186, w: 180, h: 68 };
  const edgeLayer = svg('g', {}, graph);
  const nodeLayer = svg('g', {}, graph);
  const makeNode = (agent, box, badge) => {
    const group = svg('g', { class: 'node idle' }, nodeLayer);
    svg('rect', { x: box.x, y: box.y, width: box.w, height: box.h, rx: 14 }, group);
    svg('text', { class: 'name', x: box.x + 16, y: box.y + 26 }, group).textContent = agent.name;
    svg('text', { class: 'role', x: box.x + 16, y: box.y + 43 }, group).textContent = agent.role;
    svg('circle', { class: 'dot', cx: box.x + 20, cy: box.y + box.h - 11, r: 4 }, group);
    const label = svg('text', { class: 'state', x: box.x + 30, y: box.y + box.h - 7 }, group);
    label.textContent = LABELS.idle;
    if (badge) {
      svg('circle', { class: 'badge', cx: box.x + box.w - 18, cy: box.y + 20, r: 11 }, group);
      svg('text', { class: 'badge-text', x: box.x + box.w - 18, y: box.y + 24 }, group).textContent = badge;
    }
    state.nodes[agent.id] = { group, label };
  };
  makeNode({ id: 'orchestrator', name: 'Orchestrator', role: 'Routes work, owns state' }, hub);
  SPECIALISTS.forEach((agent, index) => {
    const box = { x: 470, y: 28 + index * 100, w: 190, h: 68 };
    const cy = box.y + box.h / 2;
    const d = `M${hub.x + hub.w},${hub.y + hub.h / 2} C 340,${hub.y + hub.h / 2} 340,${cy} ${box.x},${cy}`;
    state.edges[agent.id] = svg('path', { class: 'edge', d }, edgeLayer);
    makeNode(agent, box, String(index + 1));
  });
}

function setNode(id, status, text) {
  const node = state.nodes[id];
  if (!node) return;
  node.group.setAttribute('class', `node ${status}`);
  node.label.textContent = text || LABELS[status];
}

function setEdge(id, mode) {
  if (state.edges[id]) state.edges[id].setAttribute('class', `edge ${mode}`);
}

/* ---------- stages, timeline, chat ---------- */
function renderStages(current) {
  const stages = $('#stages');
  stages.replaceChildren();
  const at = STAGES.indexOf(current);
  STAGES.forEach((name, index) => {
    const item = document.createElement('li');
    item.textContent = name;
    item.className = index < at ? 'done' : index === at ? 'current' : '';
    stages.append(item);
  });
}

function addTimeline(text, tone, detail) {
  const list = $('#timeline');
  list.querySelector('.muted')?.remove();
  const item = document.createElement('li');
  item.className = tone || '';
  item.append(text);
  if (detail) {
    const small = document.createElement('span');
    small.className = 'detail';
    small.textContent = detail.length > 180 ? `${detail.slice(0, 180)}…` : detail;
    item.append(small);
  }
  list.append(item);
  list.parentElement.scrollTop = list.parentElement.scrollHeight;
}

function addMessage(message) {
  if (state.shown.has(message.id)) return;
  state.shown.add(message.id);
  $('#messages .empty')?.remove();
  const item = document.createElement('article');
  item.className = `msg ${message.role === 'user' ? 'user' : 'agent'}`;
  const who = document.createElement('small');
  who.textContent = message.role === 'user' ? 'You' : NAMES[message.agent_id] || 'Agent';
  const body = document.createElement('div');
  body.textContent = message.content;
  item.append(who, body);
  $('#messages').append(item);
  $('#messages').scrollTop = $('#messages').scrollHeight;
}

function showError(text) {
  const item = document.createElement('article');
  item.className = 'msg error';
  item.textContent = text;
  $('#messages').append(item);
  $('#messages').scrollTop = $('#messages').scrollHeight;
}

async function syncMessages() {
  const run = await api(`/api/v1/runs/${state.runId}`);
  run.messages.forEach(addMessage);
}

/* ---------- phase (composer state) ---------- */
function setPhase(phase, hint = '') {
  state.phase = phase;
  const locked = phase === 'running' || phase === 'done' || phase === 'failed';
  $('#prompt').disabled = locked;
  $('#send').disabled = locked;
  $('#provider').disabled = state.runId !== null;
  const text = {
    idle: 'Ready',
    running: 'Agents are working…',
    waiting: 'Waiting for your answer',
    done: 'Plan ready. Start a new run to try again.',
    failed: 'Run failed. Start a new run.',
  };
  $('#status').textContent = text[phase];
  $('#hint').hidden = !hint;
  $('#hint').textContent = hint;
  $('#prompt').placeholder = phase === 'waiting' ? 'Type your answer…' : 'e.g. A module that fits a SINDy model to pendulum data, tests it, and predicts';
  if (phase === 'waiting') $('#prompt').focus();
}

/* ---------- event handling ---------- */
const providerLabel = (id) => (id === 'replay' ? 'Replay (recorded)' : id === 'openai' ? 'Live (OpenAI)' : id);

function handle(event) {
  const data = event.data;
  switch (event.type) {
    case 'workflow.started':
      setPhase('running');
      setNode('orchestrator', 'running', 'Coordinating');
      $('#run-pill').hidden = false;
      $('#run-pill').textContent = providerLabel(data.provider);
      addTimeline('Workflow started', 'blue', `Steps: ${data.steps.map((id) => NAMES[id]).join(' → ')}`);
      break;
    case 'run.stage_changed':
      renderStages(data.to);
      break;
    case 'handoff.requested':
      setEdge(data.to, 'out');
      setNode(data.to, 'running', 'Briefed');
      addTimeline(`Orchestrator → ${NAMES[data.to]}`, 'blue', data.task);
      break;
    case 'agent.started':
      setNode(data.agent_id, 'running', data.agent_id === 'orchestrator' ? 'Summarizing' : 'Working');
      break;
    case 'agent.completed': {
      const seconds = (data.latency_ms / 1000).toFixed(1);
      const tokens = (data.usage?.input_tokens ?? 0) + (data.usage?.output_tokens ?? 0);
      addTimeline(`${NAMES[data.agent_id]} replied`, 'green', `${seconds}s${tokens ? ` · ${tokens} tokens` : ''}`);
      break;
    }
    case 'message.created':
      if (!state.shown.has(data.message_id)) return syncMessages();
      break;
    case 'question.asked':
      setNode(data.agent_id, 'waiting', 'Needs you');
      setNode('orchestrator', 'waiting', 'Waiting for you');
      addTimeline(`${NAMES[data.agent_id]} needs your input`, 'amber', data.question);
      break;
    case 'workflow.paused':
      setPhase('waiting', `${NAMES[data.agent_id]} is waiting for your answer.`);
      break;
    case 'question.answered':
      setPhase('running');
      setNode(data.agent_id, 'running', 'Resumed');
      setNode('orchestrator', 'running', 'Coordinating');
      setEdge(data.agent_id, 'out');
      addTimeline('You answered', 'blue');
      break;
    case 'handoff.returned':
      setEdge(data.from, 'back');
      setNode(data.from, 'done');
      addTimeline(`${NAMES[data.from]} → Orchestrator`, 'green', data.summary);
      setTimeout(() => setEdge(data.from, 'done'), 1100);
      break;
    case 'workflow.completed':
      setPhase('done');
      setNode('orchestrator', 'done');
      addTimeline('Plan ready for review', 'green', 'Nothing was built or run.');
      break;
    case 'agent.failed':
      setPhase('failed');
      setNode(data.agent_id, 'failed');
      setEdge(data.agent_id, '');
      addTimeline(`${NAMES[data.agent_id] || data.agent_id} failed`, 'red', data.error);
      showError(`${NAMES[data.agent_id] || 'Agent'} failed: ${data.error}`);
      break;
  }
}

function openStream(after) {
  state.source?.close();
  const source = new EventSource(`/api/v1/runs/${state.runId}/events/stream?after=${after}`);
  state.source = source;
  source.addEventListener('run_event', (message) => {
    const event = JSON.parse(message.data);
    state.cursor = event.sequence;
    state.queue = state.queue.then(() => handle(event)).catch(console.error);
  });
  source.addEventListener('end', () => source.close());
}

/* ---------- actions ---------- */
function reset() {
  state.source?.close();
  Object.assign(state, { runId: null, cursor: 0, shown: new Set(), queue: Promise.resolve() });
  history.replaceState(null, '', location.pathname);
  $('#messages').replaceChildren($('#empty-template').content.cloneNode(true));
  $('#timeline').innerHTML = '<li class="muted">Events appear here as agents work.</li>';
  $('#run-pill').hidden = true;
  $('#prompt').value = '';
  buildGraph();
  renderStages('');
  setPhase('idle');
}

async function send(event) {
  event.preventDefault();
  const content = $('#prompt').value.trim();
  if (!content) return;
  const previous = state.phase;
  setPhase('running');
  try {
    if (!state.runId) {
      const run = await api('/api/v1/runs', { method: 'POST', body: JSON.stringify({ goal: content, provider: $('#provider').value }) });
      state.runId = run.id;
      history.replaceState(null, '', `?run=${run.id}`);
    }
    await api(`/api/v1/runs/${state.runId}/chat`, { method: 'POST', body: JSON.stringify({ content }) });
    $('#prompt').value = '';
    openStream(state.cursor);
  } catch (error) {
    showError(error.message);
    setPhase(previous);
  }
}

async function restore(runId) {
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.runId = runId;
    run.messages.forEach(addMessage);
    openStream(0);
  } catch (error) {
    reset();
    showError(error.message);
  }
}

async function init() {
  const config = await api('/api/v1/config');
  $('#provider').replaceChildren(...config.providers.map((p) => new Option(providerLabel(p.id), p.id)));
  $('#provider').value = config.default_provider;
  $('#composer').addEventListener('submit', send);
  $('#new-run').addEventListener('click', reset);
  // The example button is re-created by reset(), so listen on the container.
  $('#messages').addEventListener('click', (e) => {
    if (e.target.id === 'example') { $('#prompt').value = EXAMPLE; $('#prompt').focus(); }
  });
  $('#prompt').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('#composer').requestSubmit();
  });
  buildGraph();
  renderStages('');
  setPhase('idle');
  const runId = new URLSearchParams(location.search).get('run');
  if (runId) restore(runId);
}

init().catch((error) => showError(error.message));
