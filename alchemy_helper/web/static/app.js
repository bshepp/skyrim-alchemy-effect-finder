// Skyrim Alchemy Effect Finder -- plain fetch + template literals, no framework.

let EFFECTS = [];
let EFFECTS_BY_ID = {};
let INGREDIENTS = [];
let STATE = null;
let currentSavePath = null;
let showUncarried = false;

const $ = (id) => document.getElementById(id);

// HTML-escape untrusted (save-derived) strings before they reach innerHTML.
// Dataset-derived text (ingredient/effect names) is committed, trusted JSON
// and is intentionally left alone.
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

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
  // Saves are newest-first; preselect the newest so Load is one click,
  // without auto-loading it.
  if (saves.length > 0) {
    saveSelect.value = saves[0].path;
  }
}

async function refreshState() {
  STATE = await fetch('/api/state').then((r) => r.json());
  // Seed currentSavePath from the server so Reload survives a page
  // refresh (the server remembers player.save_path; JS state doesn't).
  if (!currentSavePath && STATE.save_path) {
    currentSavePath = STATE.save_path;
  }
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

  if (STATE.version) $('app-version').textContent = `v${STATE.version}`;

  renderUnknownFormsBanner();
}

function renderUnknownFormsBanner() {
  const banner = $('unknown-forms-banner');
  const forms = STATE.unknown_forms || [];
  if (forms.length === 0) {
    banner.hidden = true;
    banner.innerHTML = '';
    return;
  }
  const items = forms
    .map((f) => {
      const hexId = f.form_id.toString(16).toUpperCase().padStart(6, '0');
      return `<li>${esc(f.plugin)} (0x${hexId})</li>`;
    })
    .join('');
  banner.hidden = false;
  banner.innerHTML = `⚠ ${forms.length} unknown ingredient(s) in your save – the dataset may not match your game`
    + `<ul class="unknown-forms-list">${items}</ul>`;
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

const COMBINATORICS_ERROR_MSG =
  'the combinatorics backend returned an error – check the server console';

// New-issue URL with the app version prefilled into the title. Deliberately
// nothing else: paths and character names are the user's to volunteer.
function bugReportUrl() {
  const version = STATE?.version ? `v${STATE.version}` : 'unknown version';
  return 'https://github.com/bshepp/skyrim-alchemy-effect-finder/issues/new'
    + `?template=bug_report.yml&title=${encodeURIComponent(`[${version}] `)}`;
}

function renderBanner(container, message, variant = 'amber') {
  const report = variant === 'red'
    ? ` <a href="${bugReportUrl()}" target="_blank" rel="noopener">Report this bug</a>`
    : '';
  container.innerHTML = `<div class="banner-${variant}">${message}${report}</div>`;
}

async function findCombos() {
  const effectId = $('effect-select').value;
  const results = $('finder-results');
  if (!effectId) {
    results.innerHTML = '<p class="hint">Choose an effect first.</p>';
    return;
  }
  const onlyInventory = $('only-inventory-check').checked;
  const r = await fetch(
    `/api/combos?effect=${encodeURIComponent(effectId)}&only_inventory=${onlyInventory}`
  );
  const data = await r.json().catch(() => null);

  if (!r.ok || !data || !Array.isArray(data.combos)) {
    renderBanner(results, COMBINATORICS_ERROR_MSG, 'red');
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

function carryingNothing() {
  return !Object.values(STATE?.inventory || {}).some((n) => n > 0);
}

const EMPTY_INVENTORY_MSG =
  "You're not carrying any ingredients – load a save, or set counts in the Discovery Tracker.";

async function computePlan() {
  const results = $('plan-results');
  if (carryingNothing()) {
    results.innerHTML = `<p class="hint">${EMPTY_INVENTORY_MSG}</p>`;
    return;
  }
  results.innerHTML = '<p class="hint">computing…</p>';
  const r = await fetch('/api/discovery-plan');
  const data = await r.json().catch(() => null);

  if (!r.ok || !data || !Array.isArray(data.plan)) {
    renderBanner(results, COMBINATORICS_ERROR_MSG, 'red');
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

async function findBestPotions() {
  const results = $('potions-results');
  if (carryingNothing()) {
    results.innerHTML = `<p class="hint">${EMPTY_INVENTORY_MSG}</p>`;
    return;
  }
  results.innerHTML = '<p class="hint">computing…</p>';
  const r = await fetch('/api/best-potions');
  const data = await r.json().catch(() => null);

  if (!r.ok || !data || !Array.isArray(data.potions)) {
    renderBanner(results, COMBINATORICS_ERROR_MSG, 'red');
    return;
  }
  if (data.potions.length === 0) {
    results.innerHTML =
      '<p class="hint">No craftable potions – no two carried ingredients share an effect.</p>';
    return;
  }
  results.innerHTML = data.potions
    .map((potion) => {
      const names = potion.ingredient_ids.map((id) => ingredientName(id)).join(' + ');
      const effects = potion.effect_ids.map((id) => effectName(id)).join(', ');
      const n = potion.effect_ids.length;
      return `<div class="card"><div class="card-title">${names} – ${n} effect${n === 1 ? '' : 's'}</div>
        <div class="card-sub">effects: ${effects}</div></div>`;
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
  if (td.querySelector('input')) return; // already mid-edit; don't clobber it
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
  $('find-potions-btn').addEventListener('click', findBestPotions);

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
