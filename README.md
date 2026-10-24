# Threads AI Reply (Chrome extension)

Extension ni scan post dalam Threads, minta Gemini drafkan reply (SHORT / MORE / EXPERT), lepas tu kau semak dan edit dulu. Hanya reply yang kau tanda je yang akan dipost, satu-satu, dengan delay rawak antara setiap satu.

## 1. Dapatkan Gemini API key (percuma)

1. Pergi ke https://aistudio.google.com/apikey dan login dengan akaun Google.
2. Tekan **Create API key** dan copy key tu (bermula dengan `AIza...`).
3. Free tier tak perlukan kad kredit. Ada had bilangan request seminit dan sehari, tapi untuk puluhan reply sehari memang cukup.
   - Jangan kongsi key ni dengan orang lain.
   - Ikut terma Google, data free tier boleh digunakan untuk tambah baik produk mereka.

## 2. Pasang extension

1. Download repo ni dan extract.
2. Buka Chrome, pergi ke `chrome://extensions`, kemudian hidupkan **Developer mode** (atas kanan).
3. Tekan **Load unpacked** dan pilih folder `extension/`.
4. Pin ikon extension kat toolbar.

## 3. Cara guna

1. Buka https://www.threads.com dan login. **Set bahasa Threads ke English** supaya extension jumpa butang Reply/Post.
2. Klik ikon extension. Side panel akan terbuka.
3. Dalam **⚙️ Tetapan**:
   - Paste API key, tekan **Test key**, kemudian **Simpan**.
   - Isi persona kalau nak (contoh: gaya cakap, minat).
4. Scroll feed, atau buka satu post untuk reply komen-komen dalam thread tu. Lepas tu tekan **🔍 Scan page**.
5. Tanda post yang nak reply (**Select All** / **All Comments**), kemudian tekan **SHORT**, **MORE** atau **EXPERT**.
6. **Baca dan edit setiap reply.** AI akan tulis `SKIP` (dan buang tanda) untuk topik sensitif seperti politik, agama, boikot atau kematian.
7. Tekan **▶ POST SELECTED**. Biarkan tab Threads dan side panel terbuka sampai siap. Tekan **■ STOP** kalau nak berhenti.

## Had keselamatan (boleh ubah dalam Tetapan)

| Tetapan | Default | Kenapa |
|---|---|---|
| Delay min / max | 45s / 120s | Reply terlalu laju nampak macam bot |
| Had sehari | 30 reply | Elak akaun kena had atau shadowban |

Post yang dah di-reply diingat selama 30 hari supaya tak reply dua kali.

## Amaran

- Meta tak benarkan engagement automatik secara pukal. Guna secara sederhana, dan pastikan setiap reply memang kau setuju. Risiko pada akaun adalah tanggungan sendiri.
- Threads selalu tukar struktur page. Kalau Scan tak jumpa post atau butang Reply/Post tak jumpa, selector dalam `extension/content.js` (`REPLY_LABELS`, `POST_LABELS`, `findContainer`) perlu dikemas kini.
