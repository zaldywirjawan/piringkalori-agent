# PANDUAN PEMASANGAN — AGENT KONTEN @piringkalori

Panduan ini ditulis untuk dikerjakan sekali saja, dari nol, tanpa perlu bisa
memprogram. Perkiraan waktu total: **45–60 menit**. Kerjakan berurutan —
setiap langkah menghasilkan sesuatu yang dipakai langkah berikutnya.

Kalau ada langkah yang macet, catat pesan errornya lalu tanyakan. Jangan
lanjut ke langkah berikutnya kalau langkah sebelumnya belum menghasilkan yang
diminta.

---

## Yang akan Anda punya di akhir panduan ini

- Satu repo GitHub berisi seluruh agent.
- Instagram @piringkalori tersambung ke Meta App milik Anda sendiri.
- Robot yang mengecek jadwal tiap 15 menit dan memposting yang sudah Anda setujui.
- Semua konten yang sudah tayang otomatis pindah ke folder arsip.

---

## LANGKAH 1 — Buat repo GitHub (10 menit)

Repo ini punya dua peran sekaligus: tempat kode agent, **dan** tempat file
gambar. Instagram mewajibkan gambar berada di alamat internet yang bisa dia
unduh — repo publik GitHub memenuhi itu tanpa biaya.

1. Daftar/masuk ke <https://github.com>.
2. Klik **+** (kanan atas) → **New repository**.
3. Isi:
   - **Repository name**: `piringkalori-agent`
   - **Visibility**: pilih **Public**
     > Harus Public. Instagram tidak bisa mengunduh gambar dari repo privat.
     > Yang rahasia (token) tidak disimpan di repo — disimpan terpisah di
     > Langkah 5, dan itu tetap terenkripsi meski repo-nya publik.
   - Jangan centang "Add a README".
4. Klik **Create repository**.
5. Di halaman yang muncul, klik **uploading an existing file**.
6. Buka folder `piringkalori-agent` di komputer Anda, pilih **semua isinya**,
   lalu seret ke jendela browser.
   > Kalau folder `.github` tidak ikut terseret (macOS menyembunyikan folder
   > berawalan titik), tekan `Cmd + Shift + .` di Finder untuk menampilkannya.
7. Klik **Commit changes**.

**Hasil yang harus Anda lihat:** daftar folder `brand/`, `content/`, `docs/`,
`src/`, dan file `calendar.csv` di halaman repo.

---

## LANGKAH 2 — Siapkan akun Instagram (10 menit)

Instagram Graph API hanya melayani akun **Business** atau **Creator** yang
tersambung ke sebuah **Facebook Page**. Akun pribasi tidak bisa.

1. Di aplikasi Instagram: **Settings → Account type and tools → Switch to
   professional account** → pilih **Business**.
2. Masih di menu yang sama, hubungkan ke Facebook Page:
   **Sharing and reposts → Share to other apps → Facebook** → pilih Page.
   - Belum punya Page? Buat dulu di <https://facebook.com/pages/create>,
     nama bebas (mis. "Piringkalori"). Page ini tidak perlu aktif diisi
     konten — fungsinya cuma sebagai jembatan izin.

**Hasil yang harus Anda lihat:** di Instagram, menu Settings menampilkan
"Professional account", dan nama Facebook Page yang terhubung.

---

## LANGKAH 3 — Buat Meta App & ambil token (20 menit)

Ini bagian paling teknis. Kerjakan pelan-pelan.

### 3a. Buat App

1. Buka <https://developers.facebook.com/apps> → **Create App**.
2. Use case: pilih **Other** → **Business**.
3. Nama app: `Piringkalori Agent`. Selesaikan sampai app terbuat.
4. Di dashboard app: **Add products** → cari **Instagram** → **Set up**.

### 3b. Ambil Instagram Business Account ID

1. Buka <https://developers.facebook.com/tools/explorer> (Graph API Explorer).
2. Di kanan atas, pilih app `Piringkalori Agent`.
3. Klik **Generate Access Token**, izinkan akses ke Page dan akun IG Anda.
   Saat diminta memilih izin (permissions), pastikan tercentang:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
4. Di kolom query, ketik `me/accounts` lalu **Submit**. Salin nilai `id`
   dari Page Anda.
5. Ganti query jadi `<PAGE_ID>?fields=instagram_business_account` (ganti
   `<PAGE_ID>` dengan id tadi) → **Submit**.
6. Angka yang muncul di `instagram_business_account.id` itulah
   **IG_BUSINESS_ACCOUNT_ID**. Simpan.

### 3c. Ambil token yang tidak cepat kedaluwarsa

Token dari Graph API Explorer hanya berumur ±1 jam. Ada dua pilihan:

**Pilihan A — System User Token (disarankan, tidak pernah kedaluwarsa)**

1. Buka <https://business.facebook.com/settings/system-users>.
2. **Add** → nama `piringkalori-agent`, role **Admin** → buat.
3. **Assign assets** → pilih Facebook Page Anda → beri akses penuh.
4. Klik **Generate new token** → pilih app `Piringkalori Agent` →
   centang `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement` → **Generate**.
5. **Salin token itu sekarang juga** — hanya ditampilkan satu kali.

**Pilihan B — token 60 hari (lebih cepat, tapi harus diperbarui)**

Kalau menu System Users tidak tersedia untuk akun Anda, pakai
<https://developers.facebook.com/tools/debug/accesstoken>: tempel token
pendek dari 3b, klik **Extend Access Token**. Hasilnya berlaku 60 hari, dan
Anda harus mengulang langkah ini setiap 2 bulan.

**Hasil yang harus Anda punya:** dua nilai —
`IG_BUSINESS_ACCOUNT_ID` (angka) dan `IG_ACCESS_TOKEN` (teks panjang).

> Catatan penting soal App Review: selama akun Instagram yang dipost adalah
> akun yang sama dengan pemilik app, Anda **tidak perlu** App Review dari
> Meta. App Review baru wajib kalau app dipakai untuk akun orang lain.

---

## LANGKAH 4 — API key untuk foto makanan AI (5 menit)

Pilih **satu** penyedia.

**Google Gemini (default, umumnya paling murah)**
1. Buka <https://aistudio.google.com/apikey> → **Create API key**.
2. Salin kunci yang muncul → ini `GEMINI_API_KEY`.

**OpenAI (alternatif)**
1. Buka <https://platform.openai.com/api-keys> → **Create new secret key**.
2. Salin → ini `OPENAI_API_KEY`. Lalu di repo GitHub nanti, set variable
   `IMAGE_PROVIDER` = `openai` (cara di Langkah 5).

Isi saldo secukupnya. Perkiraan: 15 konten × 4 foto ≈ **Rp 30.000–45.000**
sekali jalan. Foto yang sudah pernah dibuat tidak akan dibuat ulang.

---

## LANGKAH 5 — Masukkan semua rahasia ke GitHub (5 menit)

Nilai-nilai ini disimpan terenkripsi. Tidak akan terlihat di repo, tidak akan
muncul di log, dan tidak bisa dibaca orang lain meski repo-nya publik.

1. Buka repo → tab **Settings** → menu kiri **Secrets and variables** →
   **Actions**.
2. Tab **Secrets** → **New repository secret**, tambahkan satu per satu:

   | Name | Value |
   |---|---|
   | `IG_ACCESS_TOKEN` | token dari Langkah 3c |
   | `IG_BUSINESS_ACCOUNT_ID` | angka dari Langkah 3b |
   | `GEMINI_API_KEY` | kunci dari Langkah 4 (atau `OPENAI_API_KEY`) |

3. Tab **Variables** → **New repository variable** (opsional):

   | Name | Value | Kapan diisi |
   |---|---|---|
   | `IMAGE_PROVIDER` | `openai` | hanya kalau Anda pilih OpenAI |
   | `GRAPH_API_VERSION` | mis. `v23.0` | kalau versi default ditolak Meta |

> Cara tahu versi Graph API yang berlaku: di Graph API Explorer, versi yang
> aktif tertulis di dropdown sebelah kolom query. Pakai angka itu.

---

## LANGKAH 6 — Tes tanpa risiko (5 menit)

Sebelum apa pun tayang, pastikan robotnya membaca semua dengan benar.

1. Repo → tab **Actions** → **Render konten** → **Run workflow**
   (biarkan "buat foto AI" tidak dicentang) → **Run**.
   Tunggu sampai centang hijau. Ini menghasilkan file PNG di folder `out/`.
2. Buka folder `out/L01/carousel/` di repo. Harus ada 6 file PNG.
   Klik salah satu untuk memastikan gambarnya benar.
3. Tab **Actions** → **Posting ke Instagram** → **Run workflow** →
   pastikan **dry_run tercentang** → isi kode `L01` → **Run**.
4. Buka log-nya. Harus muncul daftar URL gambar dan jumlah karakter caption,
   **tanpa** benar-benar memposting.

**Kalau langkah 3 gagal** dengan pesan soal token — token belum benar,
ulangi Langkah 3c. Jangan lanjut sebelum dry run bersih.

---

## LANGKAH 7 — Tayang pertama

1. Buka `calendar.csv` di repo → klik ikon pensil (**Edit this file**).
2. Ubah tanggal & jam baris `L01-feed` ke waktu yang Anda mau (WIB).
3. Ubah kolom `status` dari `draft` menjadi `approved`.
4. **Commit changes**.

Robot akan mengeceknya dalam 15 menit dan memposting saat jam itu tiba.
Setelah tayang, `status` otomatis berubah jadi `posted`, kolom `permalink`
terisi, dan folder kontennya pindah ke `archive/`.

> **Mengubah `status` menjadi `approved` adalah satu-satunya cara sebuah
> konten bisa tayang.** Selama masih `draft` atau `review`, robot akan
> melewatinya. Itulah rem tangan Anda.

---

## Kalau ada yang salah

| Gejala | Artinya | Yang dilakukan |
|---|---|---|
| `Graph API 190` | Token kedaluwarsa/dicabut | Ulangi Langkah 3c, perbarui secret |
| `Graph API 100 ... media_url` | Gambar tidak bisa diunduh Meta | Pastikan repo **Public** dan file PNG-nya ada di `out/` |
| `Container tidak selesai diproses` | Instagram lambat/gambar terlalu besar | Jalankan ulang; kalau berulang, kecilkan file PNG |
| Workflow tidak jalan sama sekali | GitHub menonaktifkan schedule di repo yang lama tidak disentuh | Buka tab Actions → **Enable workflow** |
| Status jadi `failed` | Ada error, konten TIDAK tayang | Baca kolom `catatan` di calendar.csv |

Jadwal GitHub Actions bisa telat beberapa menit saat server ramai — itu
normal. Karena itu ada toleransi 6 jam (`GRACE_HOURS`): konten tetap tayang
walau runner telat, tapi tidak akan tiba-tiba tayang keesokan harinya.
