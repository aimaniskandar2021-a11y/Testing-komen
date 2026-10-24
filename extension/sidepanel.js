import { generateReply, listModels } from './gemini.js';

const DEFAULTS = {
  apiKey: '',
  model: 'gemini-2.5-flash',
  persona: '',
  delayMin: 45,
  delayMax: 120,
  dailyCap: 30,
};
const THREADS_URLS = ['https://www.threads.com/*', 'https://www.threads.net/*'];

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let settings = { ...DEFAULTS };
let posts = []; // { ...post, selected, reply, note, err }
let replied = {}; // id -> timestamp
let busy = false;
let stopRequested = false;

// ---------- storage ----------
const today = () => new Date().toLocaleDateString('en-CA');

async function loadAll() {
  const s = await chrome.storage.local.get(['settings', 'replied', 'daily']);
  settings = { ...DEFAULTS, ...(s.settings || {}) };
  replied = s.replied || {};
  // Buang rekod lebih 30 hari.
  const cutoff = Date.now() - 30 * 864e5;
  for (const [id, t] of Object.entries(replied)) if (t < cutoff) delete replied[id];
  for (const k of Object.keys(DEFAULTS)) $(k).value = settings[k];
  await refreshToday();
}

async function getDaily() {
  const { daily } = await chrome.storage.local.get('daily');
  return daily && daily.date === today() ? daily.count : 0;
}

async function bumpDaily() {
  const count = (await getDaily()) + 1;
  await chrome.storage.local.set({ daily: { date: today(), count } });
  return count;
}

async function refreshToday() {
  $('todayCount').textContent = `Hari ni ${await getDaily()}/${settings.dailyCap}`;
}

// ---------- tab Threads ----------
async function threadsTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true, url: THREADS_URLS });
  if (!tab) throw new Error('Tab aktif bukan threads.com. Buka Threads dalam tab ni dulu.');
  return tab;
}

async function sendToTab(msg) {
  const tab = await threadsTab();
  try {
    return await chrome.tabs.sendMessage(tab.id, msg);
  } catch {
    // Tab dibuka sebelum extension dipasang: suntik content script dulu.
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
    return chrome.tabs.sendMessage(tab.id, msg);
  }
}

// ---------- UI ----------
function setStatus(text, isErr = false) {
  $('status').textContent = text;
  $('status').style.color = isErr ? '#d03030' : '';
}

function setBusy(on) {
  busy = on;
  document.querySelectorAll('.toolbar button').forEach((b) => (b.disabled = on));
  $('stop').hidden = !on;
  $('stop').disabled = false;
}

function updateCount() {
  $('selectedCount').textContent = `Selected ${posts.filter((p) => p.selected).length}`;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  e.append(...children.filter((c) => c != null));
  return e;
}

function renderItem(p) {
  const cb = el('input', { type: 'checkbox' });
  cb.checked = p.selected;
  cb.addEventListener('change', () => {
    p.selected = cb.checked;
    updateCount();
  });

  const reply = el('textarea', { class: 'reply', placeholder: 'AI reply (boleh edit sebelum post)' });
  reply.value = p.reply || '';
  reply.addEventListener('input', () => (p.reply = reply.value));

  const media = p.media.length
    ? el('div', { class: 'media' }, ...p.media.map((src) => el('img', { src, referrerpolicy: 'no-referrer', alt: '' })))
    : null;

  const isDone = !!replied[p.id];
  return el(
    'div',
    { class: `item${isDone ? ' done' : ''}`, 'data-id': p.id },
    el(
      'div',
      { class: 'head' },
      cb,
      el('span', { class: `badge${p.type === 'COMMENT' ? ' comment' : ''}` }, p.type === 'COMMENT' ? 'KOMEN' : 'OP'),
      el('a', { href: p.url, target: '_blank' }, `@${p.user}`),
      el('span', { class: 'muted' }, p.timeLabel),
      isDone ? el('span', { class: 'muted' }, '✓ dah reply') : null
    ),
    el('div', { class: 'content' }, p.text || '(tiada teks)'),
    media,
    reply,
    el('div', { class: `note${p.err ? ' err' : ''}` }, p.note || '')
  );
}

function render() {
  $('list').replaceChildren(...posts.map(renderItem));
  updateCount();
}

function updateItem(p) {
  const old = $('list').querySelector(`[data-id="${CSS.escape(p.id)}"]`);
  if (old) old.replaceWith(renderItem(p));
}

// ---------- actions ----------
async function scan() {
  try {
    setStatus('Scanning...');
    const res = await sendToTab({ type: 'scan' });
    const prev = new Map(posts.map((p) => [p.id, p]));
    posts = res.posts.map((p) => {
      const old = prev.get(p.id);
      return { ...p, selected: old?.selected || false, reply: old?.reply || '', note: old?.note || '', err: old?.err };
    });
    render();
    setStatus(
      posts.length
        ? `Jumpa ${posts.length} post. Tanda yang nak reply, pilih SHORT / MORE / EXPERT.`
        : 'Tak jumpa post. Scroll sikit supaya post muncul, kemudian Scan semula.',
      !posts.length
    );
  } catch (e) {
    setStatus(e.message, true);
  }
}

async function generate(tone) {
  if (!settings.apiKey) return setStatus('Masukkan Gemini API key dalam Tetapan dulu.', true);
  const targets = posts.filter((p) => p.selected && !replied[p.id]);
  if (!targets.length) return setStatus('Tanda sekurang-kurangnya satu post (yang belum di-reply).', true);

  setBusy(true);
  stopRequested = false;
  let i = 0;
  for (const p of targets) {
    if (stopRequested) break;
    setStatus(`Jana reply ${tone} ${++i}/${targets.length}...`);
    try {
      const text = await generateReply({ ...settings, tone, post: p });
      if (text.toUpperCase() === 'SKIP') {
        p.reply = '';
        p.selected = false;
        p.note = 'AI skip: topik sensitif / konteks tak jelas. Tulis sendiri kalau nak reply.';
        p.err = false;
      } else {
        p.reply = text;
        p.note = `${tone} · semak dulu sebelum post`;
        p.err = false;
      }
    } catch (e) {
      p.note = e.message;
      p.err = true;
    }
    updateItem(p);
    await sleep(1500); // elak kena had rate free tier
  }
  updateCount();
  setBusy(false);
  setStatus(stopRequested ? 'Dihentikan.' : 'Siap. Baca & edit reply, kemudian tekan POST SELECTED.');
}

async function postSelected() {
  const targets = posts.filter((p) => p.selected && p.reply.trim() && !replied[p.id]);
  if (!targets.length) return setStatus('Tiada post bertanda yang ada teks reply.', true);
  if (!confirm(`Post ${targets.length} reply ke Threads? Pastikan kau dah baca semuanya.`)) return;

  setBusy(true);
  stopRequested = false;
  let done = 0;
  for (const [idx, p] of targets.entries()) {
    if (stopRequested) break;
    if ((await getDaily()) >= settings.dailyCap) {
      setStatus(`Had sehari (${settings.dailyCap}) dah capai. Sambung esok.`, true);
      break;
    }
    setStatus(`Posting ${idx + 1}/${targets.length} → @${p.user}...`);
    try {
      const res = await sendToTab({ type: 'reply', id: p.id, text: p.reply.trim() });
      if (!res?.ok) throw new Error(res?.error || 'Gagal');
      replied[p.id] = Date.now();
      await chrome.storage.local.set({ replied });
      await bumpDaily();
      await refreshToday();
      p.selected = false;
      p.note = 'Berjaya dipost ✓';
      p.err = false;
      done++;
    } catch (e) {
      p.note = e.message;
      p.err = true;
    }
    updateItem(p);
    updateCount();

    if (idx < targets.length - 1 && !stopRequested) {
      const wait = Math.round(settings.delayMin + Math.random() * (settings.delayMax - settings.delayMin));
      for (let s = wait; s > 0 && !stopRequested; s--) {
        setStatus(`Tunggu ${s}s sebelum reply seterusnya (nampak lebih natural)...`);
        await sleep(1000);
      }
    }
  }
  setBusy(false);
  setStatus(`${done} reply dipost.${stopRequested ? ' Dihentikan.' : ''}`);
}

async function saveSettings() {
  const num = (id, min) => Math.max(min, parseInt($(id).value, 10) || DEFAULTS[id]);
  settings = {
    apiKey: $('apiKey').value.trim(),
    model: $('model').value.trim() || DEFAULTS.model,
    persona: $('persona').value.trim(),
    delayMin: num('delayMin', 5),
    delayMax: num('delayMax', 5),
    dailyCap: num('dailyCap', 1),
  };
  if (settings.delayMax < settings.delayMin) settings.delayMax = settings.delayMin;
  await chrome.storage.local.set({ settings });
  for (const k of Object.keys(DEFAULTS)) $(k).value = settings[k];
  await refreshToday();
  $('settingsMsg').textContent = 'Disimpan ✓';
}

async function testKey() {
  const key = $('apiKey').value.trim();
  if (!key) return ($('settingsMsg').textContent = 'Masukkan API key dulu.');
  $('settingsMsg').textContent = 'Menguji...';
  try {
    const models = await listModels(key);
    $('models').replaceChildren(...models.map((m) => el('option', { value: m })));
    $('settingsMsg').textContent = `Key OK ✓ (${models.length} model). Klik kotak Model untuk pilih.`;
  } catch (e) {
    $('settingsMsg').textContent = `Gagal: ${e.message}`;
  }
}

// ---------- wiring ----------
$('scan').addEventListener('click', scan);
document.querySelectorAll('.tone').forEach((b) => b.addEventListener('click', () => generate(b.dataset.tone)));
$('postSelected').addEventListener('click', postSelected);
$('stop').addEventListener('click', () => {
  stopRequested = true;
  $('stop').disabled = true;
});
$('selectAll').addEventListener('click', () => {
  const all = posts.every((p) => p.selected || replied[p.id]);
  posts.forEach((p) => (p.selected = !all && !replied[p.id]));
  render();
});
$('selectComments').addEventListener('click', () => {
  posts.forEach((p) => (p.selected = p.type === 'COMMENT' && !replied[p.id]));
  render();
});
$('clear').addEventListener('click', () => {
  posts = [];
  render();
  setStatus('Dikosongkan.');
});
$('saveSettings').addEventListener('click', saveSettings);
$('testKey').addEventListener('click', testKey);

loadAll().then(() => {
  if (!settings.apiKey) $('settings').open = true;
});
