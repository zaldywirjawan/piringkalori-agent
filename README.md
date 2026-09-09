# AGENT KONTEN @piringkalori

Mesin yang mengubah brief konten menjadi carousel & story Instagram jadi,
lalu menerbitkannya sesuai jadwal — dengan Anda tetap memegang rem tangan.

Baru pertama kali? Kerjakan **[docs/SETUP.md](docs/SETUP.md)** dulu.
Dokumen ini untuk pemakaian sehari-hari setelah semuanya terpasang.

---

## Cara kerjanya

```
  brief (.md)                    ← ditulis manusia / Claude, sumber kebenaran
      │
      │  ①  Claude menyusun ulang jadi data terstruktur
      ▼
  content/<KODE>/content.json    ← copy tiap slide, caption, hashtag, alt text
      │
      │  ②  src/genimages.py  (kalau butuh foto makanan)
      ▼
  content/<KODE>/img/*.png
      │
      │  ③  src/render.py       → GitHub Actions "Render konten"
      ▼
  out/<KODE>/carousel/*.png      ← 1080×1350, siap posting
  out/<KODE>/story/*.png         ← 1080×1920
      │
      │  ④  ANDA melihat & menyetujui  →  status: draft → approved
      ▼
  calendar.csv
      │
      │  ⑤  src/publish.py      → GitHub Actions "Posting ke Instagram", tiap 15 menit
      ▼
  Instagram (hashtag ikut di akhir caption)
      │
      │  ⑥  otomatis
      ▼
  archive/<YYYY-MM>/<KODE>/  +  satu baris di log-performa.csv
```

Langkah ① dikerjakan Claude. ②③⑤⑥ dikerjakan robot. **④ dikerjakan Anda** —
dan itu satu-satunya hal yang wajib Anda sentuh tiap minggu.

---

## Status sebuah konten

Kolom `status` di `calendar.csv` adalah saklar utamanya:

| Status | Artinya | Siapa yang mengubah |
|---|---|---|
| `draft` | Baru dirender, belum dilihat siapa pun | dibuat otomatis |
| `review` | Sudah dikirim ke Anda untuk dilihat | Claude |
| `approved` | **Anda setuju. Robot boleh menayangkan.** | **Anda** |
| `posted` | Sudah tayang, sudah diarsipkan | robot |
| `failed` | Dicoba tapi gagal — alasannya di kolom `catatan` | robot |
| `skipped` | Sengaja dilewat | Anda |

Selain `approved`, tidak ada status yang bisa membuat konten tayang.

---

## Rutinitas mingguan Anda (±10 menit)

1. Claude mengirimkan halaman preview berisi slide + caption minggu itu.
2. Anda buka di HP, baca, tentukan mana yang lolos.
3. Buka `calendar.csv` di GitHub → ikon pensil → ubah `draft` jadi `approved`
   pada baris yang Anda setujui → **Commit changes**.
4. Selesai. Robot mengurus sisanya, termasuk pengarsipan.

Mau menunda satu konten? Ubah saja `tanggal_posting`/`jam_posting`-nya.
Mau membatalkan? Ubah statusnya jadi `skipped`.

---

## Menambah konten baru

Satu konten = satu folder `content/<KODE>_<slug>/` berisi `content.json`.

Cara paling cepat: minta Claude membuatkannya dari brief yang sudah ada di
Google Drive (`PIRINGKALORI/02_KONTEN/<KODE>/brief/`). Claude tahu formatnya —
aturannya tertulis lengkap di [docs/SKEMA-CONTENT-JSON.md](docs/SKEMA-CONTENT-JSON.md).

Lalu di GitHub: **Add file → Create new file**, ketik nama
`content/R02_soto-betawi/content.json`, tempel isinya, **Commit**.
Workflow "Render konten" jalan sendiri dan menghasilkan PNG-nya.

Terakhir, tambahkan barisnya di `calendar.csv` dengan status `draft`.

---

## Menjalankan di komputer sendiri (opsional)

Tidak wajib — semua sudah jalan di GitHub. Ini hanya kalau Anda ingin
melihat hasil render tanpa menunggu Actions.

```bash
pip install playwright requests pillow
playwright install chromium

python3 src/render.py --all          # render semua konten
python3 src/render.py content/L01_kesalahan-diet/content.json
python3 src/genimages.py --all       # buat foto AI (butuh API key)
python3 src/publish.py --dry-run     # lihat apa yang akan tayang
```

---

## Yang TIDAK bisa diotomatiskan (batasan Meta, bukan batasan agent)

Ini jujur perlu Anda tahu supaya tidak menunggu sesuatu yang tidak akan datang:

- **Sticker interaktif di Story** — poll, kuis, countdown, link sticker.
  API Meta tidak menyediakannya sama sekali; hanya bisa lewat aplikasi HP.
  Agent tetap merender gambar story-nya, dan menuliskan sticker apa yang
  harus Anda tambahkan di field `sticker_hint`. Tempel gambarnya di app,
  tambahkan sticker, posting.
- **Reels** — bisa lewat API, tapi butuh file video yang sudah jadi. Agent
  ini belum memproduksi video; storyboard-nya sudah ada di brief.
- **Caption di Story** — Story tidak punya caption. Semua teks harus menyatu
  di gambarnya (dan memang begitu cara render.py bekerja).
- **Menjadwalkan langsung di Instagram** — API tidak punya "posting nanti".
  Karena itu robot ini yang memegang jadwalnya, bukan Instagram.
- **Statistik Story** — tidak dikembalikan oleh API. Isi manual di
  `log-performa.csv` kalau perlu.

---

## Peta folder

```
brand/            palet warna, tipografi, font — sumber gaya semua slide
content/<KODE>/   content.json + img/ (foto AI) per konten, sebelum tayang
out/<KODE>/       PNG hasil render — inilah yang diunduh Instagram
archive/<bulan>/  konten yang sudah tayang, lengkap dengan published.json
src/              render.py · genimages.py · publish.py
calendar.csv      jadwal + status — satu-satunya saklar tayang
log-performa.csv  riwayat semua yang sudah tayang, untuk evaluasi
docs/             SETUP.md (pemasangan) · SKEMA-CONTENT-JSON.md (format)
```
