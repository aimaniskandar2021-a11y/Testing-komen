// Content script untuk threads.com: baca post yang ada di page & hantar reply.
// Threads guna class name yang berubah-ubah, jadi kita bergantung pada
// struktur yang lebih stabil: link /post/<kod> yang ada <time>, link /@user,
// dan aria-label ikon Reply.
(() => {
  if (window.__threadsAiReplyLoaded) return;
  window.__threadsAiReplyLoaded = true;

  // Label ikut bahasa UI Threads. Paling selamat set Threads ke English.
  const REPLY_LABELS = ['Reply', 'Balas'];
  const POST_LABELS = ['Post', 'Siarkan', 'Siar', 'Hantar', 'Kirim'];

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = (min, max) => min + Math.random() * (max - min);

  async function waitFor(fn, timeout = 8000, step = 200) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      const v = fn();
      if (v) return v;
      await sleep(step);
    }
    return null;
  }

  function postCode(href) {
    const m = (href || '').match(/\/post\/([^/?#]+)/);
    return m ? m[1] : null;
  }

  function findReplyButton(root) {
    for (const svg of root.querySelectorAll('svg[aria-label]')) {
      if (REPLY_LABELS.includes(svg.getAttribute('aria-label'))) {
        return svg.closest('[role="button"], button') || svg;
      }
    }
    return null;
  }

  // Naik dari link masa sampai jumpa elemen yang ada butang Reply = kotak post.
  function findContainer(anchor) {
    let el = anchor.parentElement;
    while (el && el !== document.body) {
      if (findReplyButton(el)) return el;
      el = el.parentElement;
    }
    return null;
  }

  function extractText(box, user) {
    const parts = [];
    for (const span of box.querySelectorAll('span[dir="auto"]')) {
      if (span.closest('a, [role="button"], button')) continue;
      if (span.parentElement && span.parentElement.closest('span[dir="auto"]')) continue;
      const t = span.innerText.trim();
      if (t && t !== user && !parts.includes(t)) parts.push(t);
    }
    return parts.join('\n');
  }

  function extractMedia(box) {
    return [...box.querySelectorAll('img')]
      .filter((img) => !/profile|profil/i.test(img.alt || ''))
      .filter((img) => img.getBoundingClientRect().width >= 60)
      .map((img) => img.currentSrc || img.src)
      .filter(Boolean)
      .slice(0, 4);
  }

  function findPostAnchor(code) {
    return [...document.querySelectorAll('a[href*="/post/"]')].find(
      (a) => a.querySelector('time') && postCode(a.getAttribute('href')) === code
    );
  }

  function scan() {
    const pageCode = postCode(location.pathname);
    const posts = [];
    const seen = new Set();
    for (const a of document.querySelectorAll('a[href*="/post/"]')) {
      const time = a.querySelector('time');
      if (!time) continue;
      const code = postCode(a.getAttribute('href'));
      if (!code || seen.has(code)) continue;
      const box = findContainer(a);
      if (!box) continue;
      seen.add(code);
      const userLink = box.querySelector('a[href^="/@"]');
      const user = userLink ? userLink.getAttribute('href').slice(2).split(/[/?#]/)[0] : '';
      posts.push({
        id: code,
        url: new URL(a.getAttribute('href'), location.origin).href,
        user,
        // Dalam page satu post: post utama = OP, yang lain = komen orang.
        type: pageCode && code !== pageCode ? 'COMMENT' : 'OP',
        time: time.getAttribute('datetime') || '',
        timeLabel: time.textContent.trim(),
        text: extractText(box, user),
        media: extractMedia(box),
      });
    }
    return posts;
  }

  function findPostButton(dialog) {
    const btns = [...dialog.querySelectorAll('[role="button"], button')].filter(
      (b) =>
        POST_LABELS.includes(b.innerText.trim()) &&
        b.getAttribute('aria-disabled') !== 'true' &&
        !b.disabled
    );
    return btns.pop() || null;
  }

  async function typeInto(editor, text) {
    editor.focus();
    await sleep(jitter(200, 400));
    document.execCommand('insertText', false, text);
    if (!editor.innerText.trim()) {
      editor.dispatchEvent(
        new InputEvent('beforeinput', { inputType: 'insertText', data: text, bubbles: true, cancelable: true })
      );
    }
    return editor.innerText.trim().length > 0;
  }

  async function reply(id, text) {
    const anchor = findPostAnchor(id);
    if (!anchor) throw new Error('Post tak jumpa dalam page. Scroll sampai post tu nampak, kemudian Scan semula.');
    const box = findContainer(anchor);
    const btn = box && findReplyButton(box);
    if (!btn) throw new Error('Butang Reply tak jumpa (cuba tukar bahasa Threads ke English).');

    box.scrollIntoView({ block: 'center', behavior: 'smooth' });
    await sleep(jitter(500, 900));
    btn.click();

    const editor = await waitFor(() => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      const d = dialogs[dialogs.length - 1];
      return d && d.querySelector('[contenteditable="true"]');
    });
    if (!editor) throw new Error('Kotak reply tak terbuka.');

    if (!(await typeInto(editor, text))) throw new Error('Gagal taip teks dalam kotak reply.');
    await sleep(jitter(600, 1200));

    const dialog = editor.closest('[role="dialog"]') || document;
    const postBtn = await waitFor(() => findPostButton(dialog), 5000);
    if (!postBtn) throw new Error('Butang Post tak jumpa.');
    postBtn.click();

    const closed = await waitFor(() => !editor.isConnected, 15000);
    if (!closed) throw new Error('Kotak reply tak tutup, tak pasti berjaya. Semak manual.');
    return true;
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === 'scan') {
      sendResponse({ ok: true, posts: scan() });
      return false;
    }
    if (msg.type === 'reply') {
      reply(msg.id, msg.text)
        .then(() => sendResponse({ ok: true }))
        .catch((e) => sendResponse({ ok: false, error: e.message }));
      return true;
    }
    return false;
  });
})();
