const $ = (selector) => document.querySelector(selector);
const SVG = 'http://www.w3.org/2000/svg';
const STAGES = ['intake', 'planning', 'architecture', 'building', 'qa', 'review'];
const EXAMPLE = 'Build a module where learners fit a SINDy model to noisy pendulum data, test it on held-out data, and predict future motion.';
const HUB = { id: 'project_manager', name: 'Project Manager', role: 'Scopes, routes, owns the plan' };
const SPECIALISTS = [
  { id: 'researcher', name: 'Researcher', role: 'Model, inputs, algorithm' },
  { id: 'builder', name: 'Module Builder', role: 'Design, code, fixes' },
  { id: 'tester', name: 'Tester', role: 'Test plan, evidence' },
];
const NAMES = { [HUB.id]: HUB.name, ...Object.fromEntries(SPECIALISTS.map((a) => [a.id, a.name])) };
const LABELS = { idle: 'Idle', running: 'Working', waiting: 'Needs you', done: 'Done', failed: 'Failed' };

const state = { projectId: null, project: null, runId: null, cursor: 0, phase: 'idle', source: null, shown: new Set(), queue: Promise.resolve(), nodes: {}, edges: {} };

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
  makeNode(HUB, hub);
  SPECIALISTS.forEach((agent, index) => {
    const box = { x: 470, y: 40 + index * 146, w: 190, h: 68 };
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
  const at = STAGES.indexOf(current === 'repair' ? 'qa' : current);
  STAGES.forEach((name, index) => {
    const item = document.createElement('li');
    item.textContent = name;
    item.className = index < at ? 'done' : index === at ? 'current' : '';
    stages.append(item);
  });
}

// Agent activity is rendered inline in the chat feed, in event order.
function addTimeline(text, tone, detail) {
  $('#messages .empty')?.remove();
  const item = document.createElement('div');
  item.className = `evt ${tone || ''}`;
  const title = document.createElement('span');
  title.className = 'evt-title';
  title.textContent = text;
  item.append(title);
  if (detail) {
    const small = document.createElement('span');
    small.className = 'evt-detail';
    small.textContent = detail.length > 180 ? `${detail.slice(0, 180)}…` : detail;
    item.append(small);
  }
  $('#messages').append(item);
  $('#messages').scrollTop = $('#messages').scrollHeight;
}

function addMessage(message) {
  if (state.shown.has(message.id)) return;
  state.shown.add(message.id);
  $('#messages .empty')?.remove();
  const item = document.createElement('article');
  item.className = `msg ${message.role === 'user' ? 'user' : 'agent'}${message.content.includes('PROJECT PLAN:') ? ' plan' : ''}`;
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
  const locked = phase === 'running' || phase === 'plan' || phase === 'failed';
  $('#prompt').disabled = locked;
  $('#send').disabled = locked;
  $('#approve').hidden = phase !== 'plan';
  if (phase === 'built' && $('#mode-row').hidden) document.querySelector('input[name=mode][value=change]').checked = true;
  $('#mode-row').hidden = phase !== 'built';
  const text = {
    idle: 'Ready',
    running: 'Agents are working…',
    waiting: 'Waiting for your answer',
    plan: 'Plan ready. Approve it to start the build.',
    built: 'Module built. Describe a change, or start a new run.',
    failed: 'Run failed. Start a new run.',
  };
  $('#status').textContent = text[phase];
  $('#hint').hidden = !hint;
  $('#hint').textContent = hint;
  $('#prompt').placeholder = phase === 'waiting' ? 'Type your answer…' : phase === 'built' ? 'Describe a change (layout, labels, colours…) or a new feature' : 'e.g. A module that fits a SINDy model to pendulum data, tests it, and predicts';
  if (phase === 'waiting') $('#prompt').focus();
}

/* ---------- event handling ---------- */

function handle(event) {
  const data = event.data;
  const hub = HUB.id;
  switch (event.type) {
    case 'workflow.started':
      setPhase('running');
      setNode(hub, 'running', 'Coordinating');
      addTimeline('Workflow started', 'blue', `Steps: ${[...new Set(data.steps)].map((id) => NAMES[id]).join(' → ')}`);
      break;
    case 'run.stage_changed':
      renderStages(data.to);
      break;
    case 'handoff.requested':
      setEdge(data.to, 'out');
      setNode(data.to, 'running', 'Briefed');
      addTimeline(`${NAMES[data.from]} → ${NAMES[data.to]}`, 'blue', data.task);
      break;
    case 'agent.started': {
      const label = data.agent_id === hub ? (data.step === 0 ? 'Scoping' : 'Writing plan') : 'Working';
      setNode(data.agent_id, 'running', label);
      addTimeline(`${NAMES[data.agent_id]} loaded ${data.skills.length} skills`, '', `${data.skills.join(', ')} · ~${data.prompt_tokens_est} prompt tokens`);
      break;
    }
    case 'agent.completed': {
      const seconds = (data.latency_ms / 1000).toFixed(1);
      const tokens = (data.usage?.input_tokens ?? 0) + (data.usage?.output_tokens ?? 0);
      const retry = data.attempts > 1 ? ` · ${data.attempts} attempts` : '';
      addTimeline(`${NAMES[data.agent_id]} replied`, 'green', `${seconds}s${tokens ? ` · ${tokens} tokens` : ''}${retry}`);
      break;
    }
    case 'artifact.accepted':
      addTimeline(`${data.name} accepted`, 'green', data.summary);
      break;
    case 'artifact.rejected':
      addTimeline(`${data.name} rejected (attempt ${data.attempt})`, 'amber', data.errors.join('; '));
      break;
    case 'plan.ready':
      addTimeline('Project plan ready for approval', 'green', 'Nothing has been built or run.');
      break;
    case 'plan.approved':
      setPhase('running');
      addTimeline('You approved the plan', 'blue', 'The Builder starts writing the module.');
      break;
    case 'build.files_written':
      addTimeline(`${data.label}: ${data.files.length} file(s) written`, 'blue', `${data.files.join(', ')}${data.commit ? ` · snapshot ${data.commit}` : ''}`);
      break;
    case 'build.checks':
      addTimeline(data.passed ? 'Automated tests passed' : `Automated tests failed${data.round ? ` (after repair ${data.round})` : ''}`,
        data.passed ? 'green' : 'red', data.passed ? `${data.command} · ${(data.duration_ms / 1000).toFixed(1)}s` : data.output.slice(-200));
      break;
    case 'build.completed':
      setPhase('built');
      [...SPECIALISTS.map((a) => a.id), hub].forEach((id) => setNode(id, 'done'));
      addTimeline(data.kind === 'feature' ? 'Feature verified' : 'Build verified', 'green', `${data.version} · ${data.files.length} files in the module`);
      scheduleRefresh();
      break;
    case 'build.failed':
      if (data.rolled_back) setPhase('failed', 'The feature could not pass the tests and the module was restored. Start a new feature with a more specific description.');
      else setPhase('built', 'The build could not pass its own tests. Describe the problem for the Builder, or start a new run.');
      scheduleRefresh();
      addTimeline('Build failed its tests', 'red', data.reason);
      break;
    case 'revision.requested':
      setPhase('running');
      addTimeline(`Change request ${data.number}`, 'blue', data.request);
      break;
    case 'revision.completed':
      setPhase('built');
      scheduleRefresh();
      addTimeline(`Change ${data.number} applied`, 'green', `${data.files.join(', ')}`);
      break;
    case 'revision.failed':
      setPhase('built', 'That change could not be applied safely; the module was restored.');
      addTimeline(`Change ${data.number} rolled back`, 'amber', 'Tests did not pass, previous version restored.');
      break;
    case 'message.created':
      if (!state.shown.has(data.message_id)) return syncMessages();
      break;
    case 'question.asked':
      setNode(data.agent_id, 'waiting', 'Needs you');
      addTimeline(`${NAMES[data.agent_id]} needs your input`, 'amber', data.question);
      break;
    case 'workflow.paused':
      setPhase('waiting', `${NAMES[data.agent_id]} is waiting for your answer.`);
      break;
    case 'question.answered':
      setPhase('running');
      setNode(data.agent_id, 'running', 'Resumed');
      addTimeline('You answered', 'blue');
      break;
    case 'handoff.returned':
      setEdge(data.from, 'back');
      setNode(data.from, 'done');
      addTimeline(`${NAMES[data.from]} → ${NAMES[data.to]}`, 'green', data.summary);
      setTimeout(() => setEdge(data.from, 'done'), 1100);
      break;
    case 'workflow.completed':
      setPhase('plan');
      setNode(hub, 'done');
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
function emptyState() {
  const node = $('#empty-template').content.cloneNode(true);
  if (state.project?.versions > 0) {
    node.querySelector('h2').textContent = 'Describe a feature to add';
    node.querySelector('p').textContent = 'The agents research and plan the feature first, exactly like the first build, using the module that already exists in this project.';
  } else if (state.project) {
    node.querySelector('h2').textContent = `Describe the module for ${state.project.name}`;
  }
  return node;
}

function syncUrl() {
  const params = new URLSearchParams();
  if (state.projectId) params.set('project', state.projectId);
  if (state.runId) params.set('run', state.runId);
  history.replaceState(null, '', params.size ? `?${params}` : location.pathname);
}

function resetConsole() {
  state.source?.close();
  Object.assign(state, { runId: null, cursor: 0, shown: new Set(), queue: Promise.resolve() });
  $('#messages').replaceChildren(emptyState());
  $('#prompt').value = '';
  buildGraph();
  renderStages('');
  setPhase('idle');
  populateRuns();
  syncUrl();
}

// "New run" / "New feature" button: a blank console that creates a run in the current project.
const reset = resetConsole;

/* ---------- home and projects ---------- */
const RUN_STATUS = {
  active: ['Working', 'blue'], awaiting_user: ['Needs you', 'amber'], ready_for_review: ['Ready', 'green'],
  needs_review: ['Needs review', 'amber'], failed: ['Failed', 'amber'],
};

function projectCard(project) {
  const wrap = document.createElement('div');
  wrap.className = 'project-wrap';
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'project-card';
  const latest = project.runs[0];
  const title = document.createElement('h2');
  title.textContent = project.name;
  const goal = document.createElement('p');
  goal.textContent = latest ? latest.goal : 'No runs yet. Open it and describe the module.';
  const meta = document.createElement('div');
  meta.className = 'project-meta';
  const chips = [[project.versions ? `${project.versions} version${project.versions > 1 ? 's' : ''}` : 'Not built', project.versions ? 'green' : 'amber'],
    [`${project.run_count} run${project.run_count === 1 ? '' : 's'}`, '']];
  if (latest && RUN_STATUS[latest.status]) chips.push(RUN_STATUS[latest.status]);
  chips.forEach(([text, tone]) => {
    const chip = document.createElement('span');
    chip.className = `chip ${tone}`;
    chip.textContent = text;
    meta.append(chip);
  });
  card.append(title, goal, meta);
  card.addEventListener('click', () => openProject(project.id));
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'project-delete';
  remove.setAttribute('aria-label', `Delete ${project.name}`);
  remove.title = 'Delete project';
  remove.textContent = 'Delete';
  remove.addEventListener('click', async () => {
    const runs = `${project.run_count} run${project.run_count === 1 ? '' : 's'}`;
    if (!confirm(`Delete "${project.name}"?\n\nThis permanently deletes its module files and ${runs}. This cannot be undone.`)) return;
    try {
      await api(`/api/v1/projects/${project.id}`, { method: 'DELETE' });
      showHome();
    } catch (error) {
      alert(error.message);
    }
  });
  wrap.append(card, remove);
  return wrap;
}

async function showHome() {
  state.source?.close();
  Object.assign(state, { projectId: null, project: null, runId: null });
  $('#home').hidden = false;
  $('#console').hidden = true;
  $('#new-run').hidden = true;
  $('#new-project').hidden = false;
  $('#crumb').textContent = 'Developer console';
  history.replaceState(null, '', location.pathname);
  const { items } = await api('/api/v1/projects');
  const list = $('#project-list');
  if (!items.length) {
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = 'No projects yet. Create one to start building a module.';
    list.replaceChildren(empty);
  } else {
    list.replaceChildren(...items.map(projectCard));
  }
}

function enterConsole(project) {
  state.projectId = project?.id ?? null;
  state.project = project ?? null;
  $('#home').hidden = true;
  $('#console').hidden = false;
  $('#crumb').textContent = project ? project.name : 'Developer console';
  $('#project-name-label').textContent = project ? project.name : 'Conversation';
  $('#new-run').hidden = false;
  $('#new-project').hidden = true;
  $('#new-run').textContent = project?.versions ? 'New feature' : 'New run';
  resetConsole();
}

async function openProject(id, runId) {
  try {
    const project = await api(`/api/v1/projects/${id}`);
    enterConsole(project);
    const target = runId || project.runs[0]?.id;
    if (target) await restore(target);
  } catch (error) {
    await showHome();
    alert(error.message);
  }
}

function populateRuns() {
  const select = $('#run-select');
  const runs = state.project?.runs ?? [];
  select.hidden = runs.length < 2 && !(runs.length === 1 && !state.runId);
  select.replaceChildren(...(state.runId ? [] : [new Option('New run…', '')]),
    ...runs.map((r) => new Option(`${r.kind === 'feature' ? 'Feature' : 'Module'}: ${r.goal.slice(0, 40)}`, r.id)));
  select.value = state.runId || '';
}

let refreshTimer = null;
function scheduleRefresh() {
  if (!state.projectId) return;
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    try {
      state.project = await api(`/api/v1/projects/${state.projectId}`);
      $('#new-run').textContent = state.project.versions ? 'New feature' : 'New run';
      populateRuns();
    } catch (error) { console.error(error); }
  }, 300);
}

async function send(event) {
  event.preventDefault();
  const content = $('#prompt').value.trim();
  if (!content) return;
  const previous = state.phase;
  if (previous === 'built' && document.querySelector('input[name=mode]:checked').value === 'feature') resetConsole();
  setPhase('running');
  try {
    if (!state.runId) {
      const run = await api('/api/v1/runs', { method: 'POST', body: JSON.stringify({ goal: content, project_id: state.projectId }) });
      state.runId = run.id;
      syncUrl();
      scheduleRefresh();
    }
    await api(`/api/v1/runs/${state.runId}/chat`, { method: 'POST', body: JSON.stringify({ content }) });
    $('#prompt').value = '';
    openStream(state.cursor);
  } catch (error) {
    showError(error.message);
    setPhase(state.runId ? previous : 'idle');
  }
}

async function restore(runId) {
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.runId = runId;
    syncUrl();
    populateRuns();
    run.messages.forEach(addMessage);
    openStream(0);
  } catch (error) {
    resetConsole();
    showError(error.message);
  }
}

async function init() {
  $('#composer').addEventListener('submit', send);
  $('#show-activity').addEventListener('change', (e) => $('#messages').classList.toggle('hide-activity', !e.target.checked));
  $('#new-run').addEventListener('click', resetConsole);
  $('#home-link').addEventListener('click', showHome);
  $('#new-project').addEventListener('click', () => { $('#project-form').hidden = false; $('#project-error').textContent = ''; $('#project-name').focus(); });
  $('#project-cancel').addEventListener('click', () => { $('#project-form').hidden = true; });
  $('#project-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const project = await api('/api/v1/projects', { method: 'POST', body: JSON.stringify({ name: $('#project-name').value }) });
      $('#project-form').hidden = true;
      $('#project-name').value = '';
      openProject(project.id);
    } catch (error) {
      $('#project-error').textContent = error.message;
    }
  });
  $('#run-select').addEventListener('change', (e) => (e.target.value ? openProject(state.projectId, e.target.value) : resetConsole()));
  $('#approve').addEventListener('click', async () => {
    setPhase('running');
    try {
      await api(`/api/v1/runs/${state.runId}/approve`, { method: 'POST' });
      openStream(state.cursor);
    } catch (error) {
      showError(error.message);
      setPhase('plan');
    }
  });
  // The example button is re-created by resetConsole(), so listen on the container.
  $('#messages').addEventListener('click', (e) => {
    if (e.target.id === 'example') { $('#prompt').value = EXAMPLE; $('#prompt').focus(); }
  });
  $('#prompt').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('#composer').requestSubmit();
  });
  buildGraph();
  const params = new URLSearchParams(location.search);
  const projectId = params.get('project');
  const runId = params.get('run');
  if (projectId) return openProject(projectId, runId);
  if (runId) {
    const run = await api(`/api/v1/runs/${runId}`);
    if (run.project_id) return openProject(run.project_id, runId);
    enterConsole(null);
    return restore(runId);
  }
  return showHome();
}

init().catch((error) => showError(error.message));
