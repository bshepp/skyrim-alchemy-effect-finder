// Skyrim Alchemy Helper -- plain fetch + template literals, no framework.

let EFFECTS = [];
let EFFECTS_BY_ID = {};
let INGREDIENTS = [];
let STATE = null;
let currentSavePath = null;
let showUncarried = false;

const $ = (id) => document.getElementById(id);

async function loadStaticData() {
  const [effects, ingredients, saves] = await Promise.all([
    fetch('/api/effects').then((r) => r.json()),
    fetch('/api/ingredients').then((r) => r.json()),
    fetch('/api/saves').then((r) => r.json()),
  ]);
  EFFECTS = [...effects].sort((a, b) => a.name.localeCompare(b.name));
  EFFECTS_BY_ID = Object.fromEntries(effects.map((e) => [e.id, e]));
  INGREDIENTS = [...ingredients].sort((a, b) => a.name.localeCompare(b.name));

  const effectSelect = $('effect-select');
  for (const e of EFFECTS) {
    effectSelect.append(new Option(e.name, e.id));
  }

  const saveSelect = $('save-select');
  for (const s of saves) {
    saveSelect.append(new Option(`${s.name} (${s.modified_iso})`, s.path));
  }
}

async function refreshState() {
  STATE = await fetch('/api/state').then((r) => r.json());
  renderHeader();
  renderTracker();
}

function renderHeader() {
  const badge = $('mode-badge');
  const errorMsg = $('error-msg');
  if (STATE.mode === 'save') {
    badge.textContent = `SAVE: ${STATE.character}`;
    badge.className = 'badge badge-save';
  } else {
    badge.textContent = 'MANUAL MODE';
    badge.className = 'badge badge-manual';
  }
  if (STATE.error) {
    errorMsg.hidden = false;
    errorMsg.textContent = `⚠ ${STATE.error}`;
    errorMsg.title = STATE.error;
  } else {
    errorMsg.hidden = true;
    errorMsg.textContent = '';
  }

  const total = INGREDIENTS.length * 4;
  let known = 0;
  for (const slots of Object.values(STATE.known_effects)) known += slots.length;
  $('progress').textContent = `${known} of ${total} effect-slots discovered`;
}

async function loadSavePath(path) {
  if (!path) return;
  currentSavePath = path;
  await fetch('/api/load-save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  await refreshState();
}

async function postOverride(ingredientId, fields) {
  await fetch('/api/override', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ingredient_id: ingredientId, ...fields }),
  });
  await refreshState();
}

function switchTab(name) {
  for (const btn of document.querySelectorAll('.tab-btn')) {
    btn.classList.toggle('active', btn.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll('.tab-panel')) {
    panel.classList.toggle('active', panel.id === `tab-${name}`);
  }
}

function renderBanner(container, message) {
  container.innerHTML = `<div class="banner-amber">${message}</div>`;
}

async function findCombos() {
  const effectId = $('effect-select').value;
  const results = $('finder-results');
  if (!effectId) {
    results.innerHTML = '<p class="hint">Choose an effect first.</p>';
    return;
  }
  const onlyInventory = $('only-inventory-check').checked;
  const data = await fetch(
    `/api/combos?effect=${encodeURIComponent(effectId)}&only_inventory=${onlyInventory}`
  ).then((r) => r.json());

  if (data.not_implemented) {
    renderBanner(results, data.message);
    return;
  }
  if (data.combos.length === 0) {
    results.innerHTML = '<p class="hint">No combos found.</p>';
    return;
  }
  results.innerHTML = data.combos
    .map((combo) => {
      const names = combo.ingredient_ids.map((id) => ingredientName(id)).join(' + ');
      const effects = combo.effect_ids.map((id) => effectName(id)).join(', ');
      return `<div class="card"><div class="card-title">${names}</div>
        <div class="card-sub">effects: ${effects}</div></div>`;
    })
    .join('');
}

async function computePlan() {
  const results = $('plan-results');
  const data = await fetch('/api/discovery-plan').then((r) => r.json());
  if (data.not_implemented) {
    renderBanner(results, data.message);
    return;
  }
  if (data.plan.length === 0) {
    results.innerHTML = '<p class="hint">Nothing left to discover.</p>';
    return;
  }
  results.innerHTML = data.plan
    .map((brew, i) => {
      const names = brew.ingredient_ids.map((id) => ingredientName(id)).join(' + ');
      const discovered = brew.newly_discovered
        .map(([id, slot]) => `${ingredientName(id)}: ${slotEffectName(id, slot)}`)
        .join(', ');
      return `<div class="card"><div class="card-title">Brew ${i + 1}: ${names}</div>
        <div class="card-sub">newly discovers: ${discovered || 'nothing new'}</div></div>`;
    })
    .join('');
}

function ingredientName(id) {
  const ing = INGREDIENTS.find((i) => i.id === id);
  return ing ? ing.name : id;
}

function effectName(id) {
  const e = EFFECTS_BY_ID[id];
  return e ? e.name : id;
}

function slotEffectName(ingredientId, slot) {
  const ing = INGREDIENTS.find((i) => i.id === ingredientId);
  if (!ing) return `slot ${slot}`;
  return effectName(ing.effects[slot]);
}

function renderTracker() {
  const body = $('tracker-body');
  const inventory = STATE.inventory;
  const known = STATE.known_effects;
  const rows = INGREDIENTS.filter((ing) => showUncarried || (inventory[ing.id] || 0) > 0);

  body.innerHTML = rows
    .map((ing) => {
      const count = inventory[ing.id] || 0;
      const knownSlots = known[ing.id] || [];
      const cells = ing.effects
        .map((effectId, slot) => {
          const isKnown = knownSlots.includes(slot);
          const cls = isKnown ? 'known' : 'unknown';
          const label = isKnown ? effectName(effectId) : '???';
          return `<td class="effect-cell ${cls}" data-ing="${ing.id}" data-slot="${slot}">${label}</td>`;
        })
        .join('');
      return `<tr>
        <td>${ing.name}</td>
        <td class="count-cell" data-ing="${ing.id}">${count}</td>
        ${cells}
      </tr>`;
    })
    .join('');
}

function startCountEdit(td) {
  const ingId = td.dataset.ing;
  const current = STATE.inventory[ingId] || 0;
  td.innerHTML = `<input type="number" min="0" class="count-input" value="${current}">`;
  const input = td.querySelector('input');
  input.focus();
  input.select();

  const commit = () => {
    const value = parseInt(input.value, 10);
    if (Number.isInteger(value) && value >= 0) {
      postOverride(ingId, { have: value });
    } else {
      renderTracker();
    }
  };
  input.addEventListener('blur', commit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') input.blur();
    if (e.key === 'Escape') { input.removeEventListener('blur', commit); renderTracker(); }
  });
}

function toggleEffectSlot(td) {
  const ingId = td.dataset.ing;
  const slot = parseInt(td.dataset.slot, 10);
  const current = new Set(STATE.known_effects[ingId] || []);
  if (current.has(slot)) current.delete(slot); else current.add(slot);
  postOverride(ingId, { known_slots: [...current].sort((a, b) => a - b) });
}

function wireEvents() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  $('load-btn').addEventListener('click', () => loadSavePath($('save-select').value));
  $('reload-btn').addEventListener('click', () => loadSavePath(currentSavePath));

  $('find-combos-btn').addEventListener('click', findCombos);
  $('compute-plan-btn').addEventListener('click', computePlan);

  $('show-uncarried-check').addEventListener('change', (e) => {
    showUncarried = e.target.checked;
    renderTracker();
  });

  $('tracker-body').addEventListener('click', (e) => {
    if (e.target.tagName === 'INPUT') return; // already editing this cell
    const countCell = e.target.closest('.count-cell');
    if (countCell) { startCountEdit(countCell); return; }
    const effectCell = e.target.closest('.effect-cell');
    if (effectCell) toggleEffectSlot(effectCell);
  });
}

async function init() {
  wireEvents();
  await loadStaticData();
  await refreshState();
}

init();
