// Panggilan ke Gemini API (Google AI Studio, ada free tier).
const BASE = 'https://generativelanguage.googleapis.com/v1beta';

const TONES = {
  SHORT: 'Satu ayat pendek sahaja (maksimum 15 patah perkataan). Santai, mesra, macam kawan komen.',
  MORE: '2 hingga 3 ayat. Beri pendapat sendiri atau kongsi pengalaman ringkas, boleh tutup dengan satu soalan untuk sambung perbualan.',
  EXPERT: '2 hingga 4 ayat. Beri info atau tips yang betul-betul berguna berkaitan post, nada yakin tapi tak menggurui.',
};

function systemPrompt(tone, persona) {
  return [
    'Kau tulis balasan (reply) untuk post Threads bagi pihak pengguna.',
    persona ? `Tentang pengguna: ${persona}` : '',
    `Gaya: ${TONES[tone] || TONES.SHORT}`,
    'Peraturan:',
    '- Guna bahasa yang sama dengan post (BM santai, English, atau campur ikut post).',
    '- Bunyi macam manusia sebenar. Jangan generik, sebut sesuatu yang spesifik dari post.',
    '- Tiada hashtag, tiada link, tiada promosi diri. Maksimum satu emoji.',
    '- Jangan reka fakta atau pengalaman yang tak masuk akal.',
    '- Kalau post tentang politik, agama, kaum, boikot, kematian, tragedi, penyakit serius, atau kau tak faham konteksnya, balas tepat-tepat perkataan SKIP sahaja.',
    '- Keluarkan teks reply sahaja, tanpa tanda petik atau penjelasan.',
  ]
    .filter(Boolean)
    .join('\n');
}

async function call(path, apiKey, init = {}) {
  const res = await fetch(`${BASE}/${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey, ...(init.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 429) throw new Error('Had free tier Gemini dah capai. Tunggu seminit dan cuba lagi.');
    throw new Error(data.error?.message || `Gemini error ${res.status}`);
  }
  return data;
}

export async function listModels(apiKey) {
  const data = await call('models?pageSize=200', apiKey);
  return (data.models || [])
    .filter((m) => (m.supportedGenerationMethods || []).includes('generateContent'))
    .map((m) => m.name.replace(/^models\//, ''))
    .filter((n) => n.startsWith('gemini'));
}

export async function generateReply({ apiKey, model, tone, persona, post }) {
  const userMsg = [
    `Post oleh @${post.user || 'seseorang'}${post.type === 'COMMENT' ? ' (ini komen dalam thread)' : ''}:`,
    post.text || '(tiada teks, mungkin gambar/video sahaja)',
    post.media?.length ? `(Post ini ada ${post.media.length} gambar/video.)` : '',
  ]
    .filter(Boolean)
    .join('\n');

  const data = await call(`models/${encodeURIComponent(model)}:generateContent`, apiKey, {
    method: 'POST',
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: systemPrompt(tone, persona) }] },
      contents: [{ role: 'user', parts: [{ text: userMsg }] }],
      generationConfig: { temperature: 0.9 },
    }),
  });

  const parts = data.candidates?.[0]?.content?.parts || [];
  const text = parts
    .filter((p) => !p.thought)
    .map((p) => p.text || '')
    .join('')
    .trim()
    .replace(/^["“]|["”]$/g, '');
  if (!text) throw new Error('Gemini tak bagi jawapan (mungkin disekat oleh safety filter).');
  return text;
}
