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

const state = { tab: 'agents', chatOpen: true, projectId: null, project: null, runId: null, cursor: 0, phase: 'idle', source: null, shown: new Set(), queue: Promise.resolve(), nodes: {}, edges: {} };

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
  const hub = { x: 20, y: 186, w: 224, h: 68 };
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
    const box = { x: 436, y: 40 + index * 146, w: 224, h: 68 };
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
  const locked = phase === 'running' || phase === 'plan' || phase === 'failed' || phase === 'criterion';
  $('#criterion-box').hidden = phase !== 'criterion';
  $('#prompt').disabled = locked;
  $('#send').disabled = locked;
  $('#approve').hidden = phase !== 'plan';
  if (phase !== 'failed') state.canRetry = false;
  $('#retry').hidden = !(phase === 'failed' && state.canRetry);
  if (phase === 'built' && $('#mode-row').hidden) document.querySelector('input[name=mode][value=change]').checked = true;
  $('#mode-row').hidden = phase !== 'built';
  const text = {
    idle: 'Ready',
    running: 'Agents are working…',
    waiting: 'Waiting for your answer',
    plan: 'Plan ready. Approve it to start the build.',
    built: 'Module built. Describe a change, or start a new run.',
    criterion: 'A threshold needs your decision.',
    failed: 'Run failed. Start a new run.',
  };
  $('#status').textContent = text[phase];
  $('#hint').hidden = !hint;
  $('#hint').textContent = hint;
  if (phase === 'waiting' || phase === 'plan' || phase === 'criterion') setChat(true);
  updateRail();
  $('#module-busy').hidden = !(phase === 'running' && state.project?.versions);
  syncEditor();
  $('#prompt').placeholder = phase === 'waiting' ? 'Type your answer…' : phase === 'built' ? 'Describe a change (layout, labels, colours…) or a new feature' : '';
  if (phase === 'waiting') $('#prompt').focus();
}

/* ---------- workspace: tabs, live module, files, collapsible chat ---------- */
const TABS = ['module', 'agents', 'files', 'usage'];

function showTab(name) {
  state.tab = name;
  TABS.forEach((tab) => {
    $(`#panel-${tab}`).hidden = tab !== name;
    $(`#tab-${tab}`).setAttribute('aria-selected', String(tab === name));
  });
  $('#preview-reload').hidden = name !== 'module';
  if (name === 'files') loadFiles();
  if (name === 'usage') loadUsage();
  if (name === 'module') ensurePreview(false);
}

function setChat(open) {
  state.chatOpen = open;
  $('#console').classList.toggle('chat-closed', !open);
  $('#chat-rail').hidden = open;
  $('#chat-rail').setAttribute('aria-expanded', String(open));
  updateRail();
}

// A collapsed chat must never hide a gate: show a dot whenever the agents wait for the developer.
function updateRail() {
  $('#rail-dot').hidden = state.chatOpen || !['waiting', 'plan', 'failed', 'criterion'].includes(state.phase);
}

function previewNote(text) {
  $('#module-note').textContent = text;
}

let previewCall = null;
function ensurePreview(restart) {
  // One call at a time; a plain refresh joins the call already in flight, a restart waits for it.
  if (previewCall && !restart) return previewCall;
  const run = () => doEnsurePreview(restart);
  const next = previewCall ? previewCall.then(run, run) : run();
  const tracked = next.finally(() => { if (previewCall === tracked) previewCall = null; });
  previewCall = tracked;
  return tracked;
}

async function doEnsurePreview(restart) {
  if (!state.projectId || !(state.project?.versions || state.project?.files)) {
    $('#module-frame').removeAttribute('src');
    previewNote('No module yet. Describe one in the chat and approve the plan; it appears here once it is built and tested.');
    $('#preview-state').textContent = '';
    return;
  }
  const projectId = state.projectId;
  const base = `/api/v1/projects/${projectId}/preview`;
  try {
    let info = restart ? null : await api(base);
    if (!info || info.state !== 'running') {
      $('#preview-state').textContent = 'starting…';
      previewNote('Starting the module…');
      info = await api(base, { method: 'POST' });
    }
    if (projectId !== state.projectId) return;
    if (info.state === 'running') {
      $('#preview-state').textContent = 'running';
      previewNote('');
      if ($('#module-frame').getAttribute('src') !== info.url || restart) $('#module-frame').src = info.url;
    } else {
      $('#module-frame').removeAttribute('src');
      $('#preview-state').textContent = info.state === 'no_entry' ? 'no main.py' : 'not running';
      previewNote(info.state === 'no_entry'
        ? 'This module has no main.py, so it cannot be previewed yet. Ask the Builder to add a Bokeh entry file.'
        : `The module did not start: ${info.message}\n\n${info.log || ''}`);
    }
  } catch (error) {
    previewNote(error.message);
  }
}

const editor = { runId: null, path: null, original: '', commit: null };

function setStatus(text, tone = '') {
  const node = $('#editor-status');
  node.textContent = text;
  node.className = `editor-status ${tone}`;
}

function editorLocked() {
  return state.phase === 'running';
}

function syncEditor() {
  const open = !!editor.path;
  const dirty = open && $('#file-editor').value !== editor.original;
  $('#file-editor').disabled = !open || editorLocked();
  $('#editor-save').disabled = !dirty || editorLocked();
  if (editorLocked() && open) setStatus('Agents are working; editing unlocks when they finish.', 'warn');
  else if (dirty) setStatus('Unsaved changes', 'warn');
}

async function openFile(runId, path, button) {
  if (editor.path && $('#file-editor').value !== editor.original && !confirm('Discard your unsaved changes?')) return;
  $('#file-list').querySelectorAll('button').forEach((b) => b.removeAttribute('aria-current'));
  button?.setAttribute('aria-current', 'true');
  try {
    const response = await fetch(`/api/v1/runs/${runId}/files/${path}`);
    if (!response.ok) throw new Error('Could not read this file.');
    const text = await response.text();
    Object.assign(editor, { runId, path, original: text, commit: null });
    $('#file-editor').value = text;
    $('#editor-path').textContent = path;
    $('#editor-revert').hidden = true;
    $('#check-output').hidden = true;
    setStatus('');
    syncEditor();
  } catch (error) {
    setStatus(error.message, 'warn');
  }
}

async function saveFile() {
  if (!editor.path) return;
  const content = $('#file-editor').value;
  $('#editor-save').disabled = true;
  setStatus('Saving and running the checks…');
  try {
    const result = await api(`/api/v1/runs/${editor.runId}/files/${editor.path}`, { method: 'PUT', body: JSON.stringify({ content }) });
    Object.assign(editor, { original: content, commit: result.commit });
    const ok = result.checks.passed;
    setStatus(ok ? `Saved · checks passed (${(result.checks.duration_ms / 1000).toFixed(1)}s)` : 'Saved · checks FAILED', ok ? 'ok' : 'warn');
    $('#check-output').hidden = ok;
    $('#check-output').textContent = ok ? '' : result.checks.output;
    $('#editor-revert').hidden = !result.commit;
    addTimeline(`You edited ${editor.path}`, ok ? 'green' : 'amber', ok ? 'Checks passed.' : 'Checks failed; the file was kept.');
    ensurePreview(true);
  } catch (error) {
    setStatus(error.message, 'warn');
  }
  syncEditor();
}

async function revertEdit() {
  const { runId, path, commit } = editor;
  try {
    await api(`/api/v1/runs/${runId}/revert-edit`, { method: 'POST', body: JSON.stringify({ commit }) });
    addTimeline(`You reverted your edit of ${path}`, 'blue');
    ensurePreview(true);
    editor.path = null; // reload without the unsaved-changes prompt
    await openFile(runId, path, [...$('#file-list').querySelectorAll('button')].find((b) => b.textContent === path));
    setStatus('Edit reverted', 'ok');
  } catch (error) {
    setStatus(error.message, 'warn');
  }
}

async function loadFiles() {
  const runId = state.runId || state.project?.runs?.[0]?.id;
  const list = $('#file-list');
  list.replaceChildren();
  Object.assign(editor, { runId, path: null, original: '', commit: null });
  $('#file-editor').value = '';
  $('#editor-path').textContent = 'Select a file';
  $('#editor-revert').hidden = true;
  $('#check-output').hidden = true;
  setStatus('');
  syncEditor();
  if (!runId || !(state.project?.versions || state.project?.files)) {
    setStatus('No files yet.');
    return;
  }
  try {
    const { items } = await api(`/api/v1/runs/${runId}/files`);
    items.forEach((file) => {
      const row = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = file.path;
      button.addEventListener('click', () => openFile(runId, file.path, button));
      row.append(button);
      list.append(row);
    });
  } catch (error) {
    setStatus(error.message, 'warn');
  }
}

const AGENT_LABEL = { project_manager: 'Project Manager', researcher: 'Researcher', builder: 'Module Builder', tester: 'Tester' };
const money = (value) => `$${(value || 0).toFixed(4)}`;
const words = (text) => text.split('_').join(' ');

function cell(row, text) {
  const td = document.createElement('td');
  td.textContent = text;
  row.append(td);
}

function issueList(target, items, empty) {
  target.replaceChildren(...(items.length ? items : [empty]).map((text) => {
    const li = document.createElement('li');
    li.textContent = text;
    if (!items.length) li.className = 'muted';
    return li;
  }));
}

function usageBar(item, top) {
  const bar = document.createElement('div');
  bar.className = 'usage-bar';
  bar.setAttribute('role', 'img');
  const label = AGENT_LABEL[item.agent] || item.agent;
  bar.setAttribute('aria-label', `${label}: ${money(item.cost_usd)}, ${Math.round(item.share * 100)} percent`);
  const name = document.createElement('span');
  name.textContent = label;
  const track = document.createElement('span');
  track.className = 'track';
  const fill = document.createElement('span');
  fill.className = 'fill';
  fill.style.width = `${(item.cost_usd / top) * 100}%`;
  track.append(fill);
  const value = document.createElement('span');
  value.className = 'value';
  value.textContent = `${money(item.cost_usd)} · ${Math.round(item.share * 100)}%`;
  bar.append(name, track, value);
  return bar;
}

async function loadUsage() {
  const runId = state.runId || state.project?.runs?.[0]?.id;
  try {
    if (runId) {
      const report = await api(`/api/v1/runs/${runId}/report`);
      $('#usage-run-summary').textContent = report.replayed
        ? `${report.calls} calls · replayed run, no real cost`
        : `${report.calls} calls · ${report.output_tokens} output tokens · ${money(report.cost_usd)} · ${report.repair_rounds} repair rounds · ${report.revisions} changes`;
      $('#usage-run-steps').replaceChildren(...report.steps.map((step) => {
        const row = document.createElement('tr');
        cell(row, `${AGENT_LABEL[step.agent] || step.agent}: ${step.step}`);
        cell(row, step.calls);
        cell(row, step.output_tokens);
        cell(row, step.seconds);
        cell(row, money(step.cost_usd));
        return row;
      }));
      issueList($('#usage-run-issues'), [
        ...report.rejections.map((r) => `${AGENT_LABEL[r.agent] || r.agent} output rejected (${words(r.kind)}) ×${r.count}`),
        ...report.test_failures.map((f) => `Tests failed: ${words(f.kind)} ×${f.count}`),
      ], 'No rejected output and no failed tests.');
    } else {
      $('#usage-run-summary').textContent = 'No run yet.';
      $('#usage-run-steps').replaceChildren();
      issueList($('#usage-run-issues'), [], 'Nothing to report.');
    }
    const summary = await api(`/api/v1/reports${state.projectId ? `?project_id=${state.projectId}` : ''}`);
    $('#usage-project-summary').textContent = summary.runs
      ? `${summary.runs} runs · ${money(summary.cost_usd)}${summary.avg_cost_per_built_run ? ` · ${money(summary.avg_cost_per_built_run)} per built run` : ''}`
      : 'No runs with real cost yet.';
    const top = Math.max(...summary.by_agent.map((a) => a.cost_usd), 1e-9);
    $('#usage-bars').replaceChildren(...summary.by_agent.map((a) => usageBar(a, top)));
    issueList($('#usage-recurring'), summary.recurring.map((r) => `${words(r.source.replace(':', ' '))} (${AGENT_LABEL[r.agent] || r.agent}, ×${r.count}): ${r.hint}`),
      'Nothing has recurred yet.');
  } catch (error) {
    $('#usage-run-summary').textContent = error.message;
  }
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
    case 'build.retried':
      state.canRetry = false;
      setPhase('running');
      addTimeline('Build retried', 'blue', 'The approved plan is used again.');
      break;
    case 'plan.approved':
      state.approved = true;
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
      state.built = true;
      setPhase('built');
      [...SPECIALISTS.map((a) => a.id), hub].forEach((id) => setNode(id, 'done'));
      addTimeline(data.kind === 'feature' ? 'Feature verified' : 'Build verified', 'green', `${data.version} · ${data.files.length} files in the module`);
      scheduleRefresh(true);
      break;
    case 'build.failed':
      state.built = !data.rolled_back;
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
      scheduleRefresh(true);
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
    case 'criterion.question':
      $('#criterion-title').textContent = `${data.criterion_id}: ${data.statement}`;
      $('#criterion-measured').textContent = data.measured;
      $('#criterion-current').textContent = data.current || '(see the criterion)';
      $('#criterion-proposed').textContent = data.proposed || '(none)';
      $('#criterion-reason').textContent = data.reason;
      setNode('builder', 'waiting', 'Needs you');
      addTimeline(`${data.criterion_id} cannot be reached`, 'amber', `Measured ${data.measured}; proposed ${data.proposed}.`);
      setPhase('criterion');
      break;
    case 'criterion.checked':
      if (data.verdict === 'code_bug') addTimeline('Builder: the code, not the threshold, is wrong', '', 'Repairing instead of asking.');
      break;
    case 'criterion.answered':
      setPhase('running');
      setNode('builder', 'running', 'Working');
      addTimeline(`You chose: ${{ accept: 'accept the new threshold', keep: 'keep the threshold', stop: 'stop the build' }[data.decision]}`, 'blue');
      break;
    case 'criterion.amended':
      addTimeline(`${data.criterion_id} changed: ${data.current} → ${data.proposed}`, 'green', 'Approved by you; recorded in the run.');
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
      state.canRetry = data.agent_id === 'builder' && !!state.approved && !state.built;
      // A module already exists: a failed change must not lock the chat, the developer can try again.
      if (state.built) setPhase('built', `The last change could not run: ${data.error}`);
      else setPhase('failed', state.canRetry ? 'The plan is approved and kept. Retry the build without planning again.' : '');
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
  state.approved = false;
  state.built = false;
  state.canRetry = false;
  Object.assign(state, { runId: null, cursor: 0, shown: new Set(), queue: Promise.resolve() });
  $('#messages').replaceChildren(emptyState());
  $('#prompt').value = '';
  buildGraph();
  renderStages('');
  setPhase('idle');
  populateRuns();
  syncUrl();
  showTab(state.project?.versions ? 'module' : 'agents');
}

// "New run" / "New feature" button: a blank console that creates a run in the current project.
const reset = resetConsole;

/* ---------- home and projects ---------- */
const LANES = [
  ['planning', 'Planning', 'Nothing is being planned.'],
  ['needs_you', 'Needs you', 'Nothing is waiting for you.'],
  ['building', 'Building', 'No module is being built.'],
  ['ready', 'Ready', 'No module is ready yet.'],
  ['failed', 'Failed', 'Nothing has failed.'],
];
const STRIP_LABELS = ['intake', 'planning', 'architecture', 'building', 'qa', 'review'];
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

function projectCard(project) {
  const wrap = document.createElement('div');
  wrap.className = 'project-wrap';
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'project-card';
  const title = document.createElement('h2');
  title.textContent = project.name;
  const goal = document.createElement('p');
  goal.textContent = project.title || project.summary || 'No runs yet.';
  const strip = document.createElement('div');
  strip.className = 'assay';
  strip.setAttribute('role', 'img');
  strip.setAttribute('aria-label', `Stages: ${project.strip.map((state, i) => `${STRIP_LABELS[i]} ${state}`).join(', ')}`);
  project.strip.forEach((state) => {
    const cell = document.createElement('i');
    cell.className = state;
    strip.append(cell);
  });
  const meta = document.createElement('div');
  meta.className = 'card-meta';
  const left = document.createElement('span');
  left.textContent = `${project.versions ? `v${project.versions}` : 'no module'} · ${plural(project.run_count, 'run')}`;
  const right = document.createElement('span');
  right.textContent = project.spend_usd ? `$${project.spend_usd.toFixed(2)} / $${(state.moduleBudget ?? 1).toFixed(2)}` : '';
  meta.append(left, right);
  card.append(title, goal, strip, meta);
  if (project.column === 'needs_you' || project.column === 'failed') {
    const reason = document.createElement('div');
    reason.className = `card-reason ${project.column}`;
    reason.textContent = project.reason;
    card.append(reason);
  }
  card.addEventListener('click', () => openProject(project.id));
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'project-delete';
  remove.setAttribute('aria-label', `Delete ${project.name}`);
  remove.title = 'Delete project';
  remove.textContent = 'Delete';
  remove.addEventListener('click', async () => {
    const runs = plural(project.run_count, 'run');
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

// Illustrative notebook covers. The plots do not represent measured project data.
function moduleCover(project) {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 170;
  canvas.setAttribute('aria-hidden', 'true');
  const ctx = canvas.getContext('2d');
  const clusters = /knn|neighbor|classif/i.test([project.name, project.method_name].join(' '));
  ctx.fillStyle = clusters ? '#e6f1eb' : '#eaf0fb';
  ctx.fillRect(0, 0, 640, 170);
  ctx.fillStyle = clusters ? '#abc9bf' : '#b8c8dc';
  for (let x = 12; x < 640; x += 18) {
    for (let y = 12; y < 170; y += 18) ctx.fillRect(x, y, 1.4, 1.4);
  }
  for (let i = 0; i < 72; i++) {
    const t = i / 71;
    const group = i % 3;
    const x = clusters ? 140 + group * 165 + 74 * Math.sin(i * 7.3) : 32 + 576 * t;
    const trend = 134 - 98 * t;
    const y = clusters ? 74 + 20 * group + 38 * Math.cos(i * 3.4) : trend + 24 * Math.sin(i * 5.1);
    ctx.fillStyle = clusters ? ['#217768', '#447eae', '#bd7537'][group] : '#799ecf';
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, 2 * Math.PI);
    ctx.fill();
  }
  if (!clusters) {
    ctx.strokeStyle = '#254d87';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(32, 134);
    ctx.lineTo(608, 36);
    ctx.stroke();
  }
  return canvas;
}

function libraryCard(project) {
  const card = document.createElement('article');
  card.className = 'library-card';
  const body = document.createElement('div');
  const status = document.createElement('small');
  status.textContent = LANES.find(([key]) => key === project.column)?.[1] || 'Planning';
  const heading = document.createElement('h2');
  const link = document.createElement('a');
  link.href = '?project=' + encodeURIComponent(project.id);
  link.textContent = project.title || project.name;
  heading.append(link);
  const description = document.createElement('p');
  description.textContent = project.learning_objective || project.summary || 'Open the project to define its learning objective.';
  const facts = document.createElement('dl');
  for (const [label, value] of [['Method', project.method_name || 'Awaiting research'], ['Audience', project.audience || 'To be defined']]) {
    const term = document.createElement('dt');
    term.textContent = label;
    const detail = document.createElement('dd');
    detail.textContent = value;
    facts.append(term, detail);
  }
  body.append(status, heading, description, facts);
  card.append(moduleCover(project), body);
  return card;
}

function renderLab(items, spend) {
  const library = $('#module-library');
  library.replaceChildren(...items.map(libraryCard));
  if (!items.length) library.textContent = 'Create your first project to add a module to the library.';
  const waiting = items.filter((p) => p.column === 'needs_you').length;
  const modules = items.filter((p) => p.has_module).length;
  const stats = $('#lab-stats');
  stats.replaceChildren();
  [[items.length, 'project'], [modules, 'module'], [waiting, 'waiting for you']].forEach(([n, word], i) => {
    if (i) stats.append(' · ');
    const b = document.createElement('b');
    b.textContent = n;
    stats.append(b, ` ${word === 'waiting for you' ? word : plural(n, word).replace(/^\d+ /, '')}`);
  });
  $('#lab-budget').hidden = !spend;
  if (spend) {
    const share = Math.min(1, spend.total_usd / spend.budget_usd);
    $('#budget-fill').style.width = `${Math.max(share * 100, 1)}%`;
    $('#budget-text').textContent = `$${spend.total_usd.toFixed(2)} of $${spend.budget_usd.toFixed(0)}`;
    $('#budget-meter').setAttribute('aria-label', `API spend ${spend.total_usd.toFixed(2)} of ${spend.budget_usd} dollars`);
    state.moduleBudget = spend.module_budget_usd;
  }
  const lanes = LANES.map(([key, label, empty]) => {
    const lane = document.createElement('section');
    lane.className = `lane ${key}${items.some((p) => p.column === key) ? ' has-items' : ''}`;
    lane.setAttribute('aria-label', label);
    const head = document.createElement('h2');
    head.className = 'lane-head';
    const name = document.createElement('span');
    name.textContent = label;
    const members = items.filter((p) => p.column === key);
    const count = document.createElement('span');
    count.className = 'lane-count';
    count.textContent = members.length;
    head.append(name, count);
    lane.append(head);
    if (members.length) members.forEach((p) => lane.append(projectCard(p)));
    else {
      const note = document.createElement('p');
      note.className = 'lane-empty';
      note.textContent = key === 'planning' && !items.length ? 'No projects yet. Create one to start building a module.' : empty;
      lane.append(note);
    }
    return lane;
  });
  $('#board').replaceChildren(...lanes);
}

async function showHome() {
  state.source?.close();
  Object.assign(state, { projectId: null, project: null, runId: null });
  $('#home').hidden = false;
  $('#console').hidden = true;
  $('#new-run').hidden = true;
  $('#new-project').hidden = false;
  $('#crumb').textContent = 'Lab';
  history.replaceState(null, '', location.pathname);
  const [{ items }, { spend }] = await Promise.all([api('/api/v1/projects'), api('/api/v1/spend').catch(() => ({ spend: null }))]);
  items.sort((a, b) => (b.last_activity || '').localeCompare(a.last_activity || ''));
  renderLab(items, spend);
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
function scheduleRefresh(reloadModule = false) {
  if (!state.projectId) return;
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    try {
      state.project = await api(`/api/v1/projects/${state.projectId}`);
      $('#new-run').textContent = state.project.versions ? 'New feature' : 'New run';
      populateRuns();
      if (reloadModule && (state.project.versions || state.project.files)) {
        $('#module-busy').hidden = true;
        showTab('module');
        ensurePreview(true);
      }
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
  TABS.forEach((tab) => $(`#tab-${tab}`).addEventListener('click', () => showTab(tab)));
  $('#chat-collapse').addEventListener('click', () => setChat(false));
  $('#chat-rail').addEventListener('click', () => setChat(true));
  $('#preview-reload').addEventListener('click', () => ensurePreview(true));
  $('#editor-save').addEventListener('click', saveFile);
  $('#editor-revert').addEventListener('click', revertEdit);
  $('#file-editor').addEventListener('input', syncEditor);
  $('#file-editor').addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); if (!$('#editor-save').disabled) saveFile(); }
    if (e.key === 'Tab' && !e.shiftKey) { e.preventDefault(); document.execCommand('insertText', false, '    '); }
  });
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
  [['accept', '#criterion-accept'], ['keep', '#criterion-keep'], ['stop', '#criterion-stop']].forEach(([decision, id]) => {
    $(id).addEventListener('click', async () => {
      if (decision === 'stop' && !confirm('Stop this build? The files are kept and you can still request changes.')) return;
      setPhase('running');
      try {
        await api(`/api/v1/runs/${state.runId}/criterion`, { method: 'POST', body: JSON.stringify({ decision }) });
        openStream(state.cursor);
      } catch (error) {
        showError(error.message);
        setPhase('criterion');
      }
    });
  });
  $('#retry').addEventListener('click', async () => {
    state.canRetry = false;
    setPhase('running');
    try {
      await api(`/api/v1/runs/${state.runId}/retry`, { method: 'POST' });
      openStream(state.cursor);
    } catch (error) {
      showError(error.message);
      state.canRetry = true;
      setPhase('failed', 'The plan is approved and kept. Retry the build without planning again.');
    }
  });
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
