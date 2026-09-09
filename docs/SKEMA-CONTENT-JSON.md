# SKEMA `content.json`

Dokumen ini adalah kontrak antara **penulis konten** (Claude, dari brief 13
tahap di `Master-Prompt-Konten-FINAL-v2.md`) dan **perender** (`src/render.py`).
Selama file mengikuti bentuk di sini, slide-nya pasti jadi.

Satu konten = satu folder `content/<KODE>_<slug>/` berisi `content.json`,
dan (kalau perlu foto) subfolder `img/`.

---

## Kerangka file

```jsonc
{
  "kode": "R01",                    // wajib. Sama dengan folder di Drive
  "slug": "rendang-ayam",           // wajib
  "kategori": "resep",              // resep | mitos | tips | relatable | qna
  "judul": "Rendang Ayam Diet",     // untuk arsip & log, bukan untuk slide
  "keyword_utama": "resep rendang ayam rendah kalori",   // Tahap 2
  "keyword_pendukung": ["...", "...", "..."],
  "status_uji_dapur": "BELUM DIUJI",// Aturan Wajib #3, resep saja
  "disclosure_ai": true,            // true kalau ada foto AI → label otomatis di caption

  "carousel": [ /* 3–10 slide, lihat daftar tipe di bawah */ ],
  "story":    [ /* 0–4 story */ ],

  "caption":  "…",                  // Tahap 8, teks utuh siap tempel
  "hashtag_set": "A",               // A niche | B edukasi | C komunitas
  "hashtags": "#… #… #…",           // masuk ke komentar pertama, bukan caption
  "alt_text": ["…", "…"],           // satu per slide carousel, berurutan

  "images": [                       // dipakai src/genimages.py
    { "id": "hero", "aspect": "4:5", "prompt": "Top-down photo of …" }
  ],

  "jadwal": { "tanggal": "2026-09-08", "jam": "07:00",
              "tipe": "feed_carousel", "platform": "instagram" }
}
```

**Aturan yang gampang terlewat**

- `alt_text` harus sama banyak dengan jumlah slide `carousel`, urutannya sama.
  Keyword utama wajib muncul natural di `alt_text[0]` (Tahap 2).
- `hashtags` **tidak** boleh ikut ditempel di `caption` — publish.py yang
  menaruhnya sebagai komentar pertama.
- Foto dirujuk dengan path relatif dari folder konten: `"image": "img/hero.png"`.
  Kalau file belum ada, slide tetap dirender dengan kotak "FOTO BELUM ADA" —
  jadi Anda bisa melihat layout-nya sebelum membayar generate foto.
- Di dalam teks mana pun, `**begini**` menjadi **tebal**.
- Instagram membatasi carousel maksimal **10** gambar.

---

## Tipe slide carousel

### `cover` — slide 1
```jsonc
{ "type": "cover",
  "headline": "Rendang Ayam 275 kkal",
  "subline": "Versi warung: 520 kkal. Ini bedanya di mana.",
  "badge_kalori": "275 kkal",       // opsional, muncul di kanan atas
  "badge_kategori": "RESEP DIET",   // opsional, default dari `kategori`
  "image": "img/hero.png" }         // opsional; tanpa foto → teks di tengah
```

### `compare` — tabel Biasa vs Diet (Tahap 3)
```jsonc
{ "type": "compare", "judul": "Biasa vs Versi Diet",
  "kolom": ["Biasa", "Diet"],
  "rows": [ { "label": "Kalori", "biasa": "520 kkal", "diet": "275 kkal" },
            { "label": "Protein", "biasa": "22 g", "diet": "28 g" } ],
  "catatan": "Estimasi per porsi 180 g. Sumber: TKPI Kemenkes RI." }
```
Kolom "Biasa" otomatis dicoret, kolom "Diet" otomatis ditandai hijau.
Muat nyaman sampai ±8 baris.

### `photo_callout` — bahan mentah (Tahap 6 slide 3)
```jsonc
{ "type": "photo_callout", "judul": "Bahannya cuma ini",
  "image": "img/bahan.png",
  "callouts": ["**Santan** → susu evaporasi", "**Ayam** → dada tanpa kulit"] }
```

### `steps` — cara masak (Tahap 6 slide 4)
```jsonc
{ "type": "steps", "judul": "Cara masak", "image": "img/proses.png",
  "steps": ["Tumis bumbu halus sampai wangi.", "Masukkan ayam, aduk rata."] }
```
Maksimal 5 langkah kalau ada foto, 7 kalau tanpa foto.

### `macros` — bar gizi (Tahap 6 slide 5)
```jsonc
{ "type": "macros", "judul": "Rincian per porsi",
  "porsi": "1 porsi = 180 g (±1 piring saji)",
  "items": [ { "label": "Protein", "value": 28, "unit": " g", "highlight": true },
             { "label": "Karbo",   "value": 12, "unit": " g" } ],
  "catatan": "Angka estimasi, bisa bervariasi tergantung merek bahan." }
```
Panjang bar otomatis relatif terhadap nilai terbesar. `highlight: true`
membuat satu bar berwarna coral — pakai untuk angka yang jadi bintang.

### `list` — daftar bernomor
```jsonc
{ "type": "list", "judul": "3 kesalahan yang paling sering",
  "items": [ { "headline": "Motong kalori terlalu ekstrem",
               "body": "Berakhir kalap di akhir minggu." } ] }
```

### `text` — satu poin per slide
```jsonc
{ "type": "text", "eyebrow": "Kesalahan 1", "judul": "Motong kalori ekstrem",
  "body": ["Paragraf pertama.", "Paragraf kedua."] }
```

### `quote` — kutipan besar
```jsonc
{ "type": "quote", "text": "Diet yang berhasil bukan yang paling ketat.",
  "attrib": "Tapi yang paling bisa kamu jalani bulan depan." }
```

### `cta` — slide penutup (Tahap 6 slide 6)
```jsonc
{ "type": "cta", "headline": "Kamu pernah kejebak yang mana?",
  "subtext": "Komen nomornya — aku baca satu-satu.",
  "pill": "Simpan buat dibaca ulang",
  "footer": "Konten edukatif, bukan pengganti saran medis." }
```
**Aturan Wajib #6:** jangan menjanjikan PDF/link bio di sini kalau asetnya
belum benar-benar tersedia.

---

## Story (Tahap 7)

Semua tipe story memakai bentuk yang sama; `type` hanya penanda untuk manusia.

```jsonc
{ "type": "teaser",              // teaser | process | repost | quiz
  "style": "sage",               // sage (hijau) | krem
  "eyebrow": "Nanti pagi di feed",
  "headline": "Teks besar di tengah story",
  "subline": "Kalimat pendukung.",
  "image": "img/proses.png",     // opsional
  "sticker_hint": "STICKER MANUAL: poll 2 opsi — 'A' / 'B'",
  "cta": "geser ke atas" }
```

`sticker_hint` **tidak** ditempel ke gambar sebagai instruksi — ia dicetak
kecil di bawah sebagai pengingat untuk Anda saat memposting, karena sticker
interaktif hanya bisa ditambahkan lewat aplikasi HP. Kalau sebuah story
memang butuh sticker, jangan setujui baris story-nya di `calendar.csv`;
posting manual saja.

---

## Prompt foto (Tahap 5)

`genimages.py` sudah otomatis menambahkan gaya visual yang seragam
(cahaya alami dari kiri, latar krem `#FDF8F0`, keramik matte, tanpa teks,
tanpa tangan). Jadi `prompt` cukup mendeskripsikan **isi piringnya saja**:

```jsonc
{ "id": "hero",   "aspect": "4:5", "prompt": "Top-down flat lay of Indonesian chicken rendang with reduced coconut sauce, served with a small portion of white rice and sliced red chili on a matte ceramic plate" }
{ "id": "bahan",  "aspect": "4:5", "prompt": "Flat lay of raw ingredients: skinless chicken breast, lemongrass, galangal, shallots, red chilies, evaporated milk in a small jug" }
{ "id": "proses", "aspect": "4:5", "prompt": "45-degree close-up of rendang simmering in a shallow pan, sauce reduced and glossy" }
```

Jangan menulis teks yang ingin muncul di gambar ke dalam prompt — semua teks
dirender oleh `render.py` supaya tajam dan tidak salah eja.

---

## Batas aman konten (Aturan Wajib #8)

Berlaku ke semua field teks, tanpa pengecualian:

- Tidak menjanjikan angka/tenggat penurunan berat badan.
- Tidak memoralkan makanan ("dosa", "menebus kalori dengan olahraga").
- Tidak menganjurkan defisit ekstrem atau melewatkan makan.
- Tidak memakai bahasa tubuh yang menghakimi.
- Hindari klaim "detoks" / "membakar lemak" dari satu bahan.
- Konten yang menyinggung pembatasan makan wajib ditutup kalimat:
  *"Kalau hubunganmu dengan makanan terasa membebani, itu layak dibicarakan
  dengan tenaga profesional — bukan tanda gagal."*

Kalau sebuah hook terasa kuat justru karena melanggar salah satu poin di
atas, hook itu dibuang, bukan dilunakkan.
