#!/usr/bin/env python3
"""
PENERBIT INSTAGRAM — PIRINGKALORI
=================================
Membaca calendar.csv, mencari baris yang statusnya `approved` dan jadwalnya
sudah jatuh tempo (zona waktu Asia/Jakarta), lalu menerbitkannya ke Instagram
lewat Instagram Graph API resmi.

Setelah berhasil tayang, script ini otomatis:
  1. mengisi kolom media_id, permalink, posted_at dan mengubah status -> posted
  2. menambahkan hashtag sebagai komentar pertama
  3. memindahkan konten ke archive/<YYYY-MM>/<KODE>/  (arsip)
  4. mencatat satu baris di log-performa.csv

Environment variable yang dibutuhkan:
    IG_ACCESS_TOKEN         token panjang (System User Token) dari Meta
    IG_BUSINESS_ACCOUNT_ID  ID akun Instagram Business (angka)
    PUBLIC_BASE_URL         (opsional) base URL publik untuk file gambar
    GRAPH_API_VERSION       (opsional) default v23.0

Pakai:
    python3 src/publish.py --dry-run    # lihat apa yang AKAN diposting
    python3 src/publish.py              # benar-benar posting
    python3 src/publish.py --kode L01 --force   # posting satu konten sekarang
"""

import argparse
import csv
import datetime as dt
import json
import os
import pathlib
import shutil
import sys
import time
from zoneinfo import ZoneInfo

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAL = ROOT / "calendar.csv"
LOG = ROOT / "log-performa.csv"
TZ = ZoneInfo("Asia/Jakarta")

VERSION = os.environ.get("GRAPH_API_VERSION", "v23.0")
BASE = f"https://graph.facebook.com/{VERSION}"
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IGID = os.environ.get("IG_BUSINESS_ACCOUNT_ID", "")

# Jangan posting konten yang jadwalnya sudah lewat lebih dari sekian jam —
# lebih baik dilewat daripada tiba-tiba tayang tengah malam karena runner mati.
GRACE_HOURS = int(os.environ.get("GRACE_HOURS", "6"))

# Batas keras caption Instagram. Lewat satu karakter pun, Graph API menolak
# dengan 400 "The caption was too long".
CAPTION_MAX = 2200

FIELDS = ["id", "kode", "tanggal_posting", "jam_posting", "platform", "tipe_konten",
          "status", "media_id", "permalink", "posted_at", "catatan"]


# --------------------------------------------------------------------------
# kalender
# --------------------------------------------------------------------------

def read_cal() -> list:
    if not CAL.exists():
        sys.exit(f"calendar.csv tidak ditemukan di {CAL}")
    with CAL.open(newline="", encoding="utf-8") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_cal(rows: list):
    with CAL.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def due(row: dict, now: dt.datetime) -> bool:
    try:
        sched = dt.datetime.strptime(
            f"{row['tanggal_posting']} {row['jam_posting']}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=TZ)
    except ValueError:
        return False
    return sched <= now < sched + dt.timedelta(hours=GRACE_HOURS)


# --------------------------------------------------------------------------
# URL publik gambar
# --------------------------------------------------------------------------

def public_base() -> str:
    b = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if b:
        return b + "/"
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA") or os.environ.get("GITHUB_REF_NAME") or "main"
    if not repo:
        sys.exit("PUBLIC_BASE_URL belum diisi dan tidak sedang jalan di GitHub Actions.")
    return f"https://raw.githubusercontent.com/{repo}/{sha}/"


def urls_for(kode: str, kind: str) -> list:
    d = ROOT / "out" / kode / kind
    if not d.exists():
        return []
    return [public_base() + p.relative_to(ROOT).as_posix() for p in sorted(d.glob("*.png"))]


def reel_url(kode: str) -> str:
    p = ROOT / "out" / kode / "reel" / "reel.mp4"
    return public_base() + p.relative_to(ROOT).as_posix() if p.exists() else ""


# --------------------------------------------------------------------------
# Graph API
# --------------------------------------------------------------------------

def api(method: str, path: str, **payload) -> dict:
    payload["access_token"] = TOKEN
    r = requests.request(method, f"{BASE}/{path}", data=payload, timeout=120)
    if r.status_code >= 400:
        try:
            msg = r.json()["error"]["message"]
        except Exception:  # noqa: BLE001
            msg = r.text[:300]
        raise RuntimeError(f"Graph API {r.status_code}: {msg}")
    return r.json()


def wait_ready(container_id: str, tries: int = 20):
    """Tunggu sampai container selesai diproses Instagram."""
    for _ in range(tries):
        st = requests.get(f"{BASE}/{container_id}",
                          params={"fields": "status_code,status", "access_token": TOKEN},
                          timeout=60).json()
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Container gagal diproses: {st.get('status')}")
        time.sleep(5)
    raise RuntimeError("Container tidak selesai diproses dalam batas waktu.")


def make_container(**payload) -> str:
    return api("POST", f"{IGID}/media", **payload)["id"]


def publish_container(cid: str, tries: int = 20) -> dict:
    wait_ready(cid, tries)
    res = api("POST", f"{IGID}/media_publish", creation_id=cid)
    mid = res["id"]
    perma = requests.get(f"{BASE}/{mid}",
                         params={"fields": "permalink", "access_token": TOKEN},
                         timeout=60).json().get("permalink", "")
    return {"media_id": mid, "permalink": perma}


# --------------------------------------------------------------------------
# penerbitan per tipe
# --------------------------------------------------------------------------

def post_carousel(doc: dict, kode: str) -> dict:
    urls = urls_for(kode, "carousel")
    if len(urls) < 2:
        raise RuntimeError(f"Carousel butuh minimal 2 gambar, ketemu {len(urls)}. Sudah dirender?")
    if len(urls) > 10:
        raise RuntimeError("Instagram membatasi carousel maksimal 10 gambar.")
    alts = doc.get("alt_text", [])
    children = []
    for i, u in enumerate(urls):
        p = {"image_url": u, "is_carousel_item": "true"}
        if i < len(alts):
            p["alt_text"] = alts[i]
        children.append(make_container(**p))
        time.sleep(1)
    for c in children:
        wait_ready(c)
    cid = make_container(media_type="CAROUSEL", children=",".join(children),
                         caption=caption_of(doc))
    return publish_container(cid)


def post_single(doc: dict, kode: str) -> dict:
    urls = urls_for(kode, "carousel")
    if not urls:
        raise RuntimeError("Tidak ada gambar untuk diposting.")
    p = {"image_url": urls[0], "caption": caption_of(doc)}
    if doc.get("alt_text"):
        p["alt_text"] = doc["alt_text"][0]
    return publish_container(make_container(**p))


def post_story(doc: dict, kode: str, nomor: int = 0) -> dict:
    """Posting story. `nomor` 0 = semua slide sekaligus; 1, 2, 3… = satu slide
    saja (tipe_konten `story_1`, `story_2`, … di calendar.csv), supaya teaser,
    proses, dan pengumuman "sudah tayang" bisa punya jam sendiri-sendiri.

    Catatan: API Instagram tidak bisa memasang sticker (poll, quiz, link,
    countdown). Story tayang polos; sticker hanya bisa ditambah manual.
    """
    urls = urls_for(kode, "story")
    if not urls:
        raise RuntimeError("Tidak ada gambar story untuk diposting.")
    if nomor:
        if nomor > len(urls):
            raise RuntimeError(f"Story nomor {nomor} tidak ada — hanya ada {len(urls)} slide.")
        urls = [urls[nomor - 1]]
    out = []
    for u in urls:
        out.append(publish_container(make_container(image_url=u, media_type="STORIES")))
        time.sleep(2)
    return {"media_id": ",".join(o["media_id"] for o in out),
            "permalink": out[0]["permalink"]}


def post_reel(doc: dict, kode: str) -> dict:
    """Posting Reel dari out/<KODE>/reel/reel.mp4 (dibuat src/make_reel.py)."""
    url = reel_url(kode)
    if not url:
        raise RuntimeError("Video reel belum ada. Jalankan workflow 'Render konten' dulu.")
    cap = dict(doc, caption=doc["reel_caption"]) if doc.get("reel_caption") else doc
    cid = make_container(media_type="REELS", video_url=url, caption=caption_of(cap),
                         share_to_feed="true")
    # Video diproses jauh lebih lama daripada gambar — beri waktu sampai 5 menit.
    return publish_container(cid, tries=60)


HANDLERS = {"feed_carousel": post_carousel, "feed_single": post_single,
            "story": post_story, "reel": post_reel}


def story_nomor(tipe: str) -> int:
    """`story_2` -> 2, `story` -> 0, selain story -> -1."""
    if tipe == "story":
        return 0
    if tipe.startswith("story_") and tipe[6:].isdigit():
        return int(tipe[6:])
    return -1


def jalankan(tipe: str, doc: dict, kode: str) -> dict:
    n = story_nomor(tipe)
    if n >= 0:
        return post_story(doc, kode, n)
    if tipe not in HANDLERS:
        raise RuntimeError(f"tipe_konten tidak dikenal: {tipe}")
    return HANDLERS[tipe](doc, kode)


def menunggu_feed(row: dict, doc: dict, rows: list) -> bool:
    """Story bertipe `repost` ("sudah tayang") jangan mendahului feed-nya.

    Jadwal GitHub Actions bisa telat; tanpa penjaga ini, story "resep sudah
    naik" bisa tayang padahal carousel-nya belum. Kalau kode ini memang tidak
    punya baris feed di kalender, tidak ada yang ditunggu.
    """
    n = story_nomor(row.get("tipe_konten", ""))
    stories = doc.get("story", [])
    if n < 1 or n > len(stories) or stories[n - 1].get("type") != "repost":
        return False
    feed = [x for x in rows if x["kode"] == row["kode"]
            and x.get("tipe_konten", "").startswith("feed")]
    return bool(feed) and not any(x.get("status") == "posted" for x in feed)


def caption_of(doc: dict) -> str:
    """Caption + disclosure AI + hashtag.

    Hashtag ditempel di akhir caption, bukan sebagai komentar pertama.
    Alasannya: memposting komentar lewat API butuh izin tambahan
    `instagram_manage_comments`, dan tanpa izin itu Meta menolak dengan
    error (#10). Menaruhnya di caption selalu berhasil dan tidak
    memerlukan wewenang tambahan apa pun.

    Instagram menolak caption di atas CAPTION_MAX karakter dengan
    "The caption was too long" — penolakan itu baru datang SETELAH semua
    gambar carousel diunggah, jadi kuota dan waktu sudah terbuang.
    Karena itu panjangnya diperiksa di sini, sebelum satu pun panggilan
    API dilakukan, dan gagal dengan angka yang jelas supaya ketahuan
    saat dry run.
    """
    cap = doc.get("caption", "")
    if doc.get("disclosure_ai"):
        cap += "\n\n" + json.loads(
            (ROOT / "brand" / "tokens.json").read_text(encoding="utf-8")
        )["disclosure_ai"]
    tags = doc.get("hashtags", "").strip()
    if tags:
        cap += "\n\n.\n.\n.\n" + tags

    if len(cap) > CAPTION_MAX:
        inti = len(doc.get("caption", ""))
        raise RuntimeError(
            f"Caption {len(cap)} karakter, batas Instagram {CAPTION_MAX}. "
            f"Kelebihan {len(cap) - CAPTION_MAX}. "
            f"(teks {inti} + disclosure + hashtag {len(tags)}) "
            f"Pangkas caption di content.json, jangan tambah hashtag."
        )
    return cap


# --------------------------------------------------------------------------
# arsip + log
# --------------------------------------------------------------------------

def catat_log(kode: str, row: dict, doc: dict):
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["kode", "judul", "tipe", "posted_at", "jam_posting",
                        "hashtag_set", "media_id", "permalink",
                        "save_rate", "share_rate", "comment_rate", "catatan"])
        w.writerow([kode, doc.get("judul", ""), row.get("tipe_konten", ""),
                    row.get("posted_at", ""), row.get("jam_posting", ""),
                    doc.get("hashtag_set", ""), row.get("media_id", ""),
                    row.get("permalink", ""), "", "", "", ""])


def archive(kode: str, row: dict, doc: dict, rows: list):
    stamp = dt.datetime.now(TZ).strftime("%Y-%m")
    dest = ROOT / "archive" / stamp / kode
    dest.mkdir(parents=True, exist_ok=True)
    for src, name in ((ROOT / "content" / folder_of(kode), "content"),
                      (ROOT / "out" / kode, "out")):
        if src and src.exists():
            shutil.move(str(src), str(dest / name))
    (dest / "published.json").write_text(json.dumps({
        "kode": kode, "judul": doc.get("judul"),
        "media_id": row.get("media_id"), "permalink": row.get("permalink"),
        "posted_at": row.get("posted_at"), "tipe": row.get("tipe_konten"),
        "hashtag_set": doc.get("hashtag_set"),
        # semua tayangan kode ini (feed, story, reel), bukan cuma yang terakhir
        "tayangan": [{"tipe": x.get("tipe_konten"), "media_id": x.get("media_id"),
                      "permalink": x.get("permalink"), "posted_at": x.get("posted_at")}
                     for x in rows if x["kode"] == kode and x.get("status") == "posted"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def folder_of(kode: str):
    for p in (ROOT / "content").glob(f"{kode}_*"):
        return p.name
    return None


def load_doc(kode: str) -> dict:
    f = folder_of(kode)
    if not f:
        raise RuntimeError(f"Folder konten untuk {kode} tidak ditemukan di content/")
    return json.loads((ROOT / "content" / f / "content.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# pemeriksa caption
# --------------------------------------------------------------------------

def cek_token() -> int:
    """Tanya ke server Meta apakah token benar-benar hidup dan berwenang.

    Ini ada karena `--dry-run` TIDAK menyentuh Meta sama sekali, dan run
    terjadwal yang tidak menemukan jadwal juga berhenti sebelum memakai
    token. Keduanya bisa "sukses" padahal token sudah mati — yang baru
    ketahuan saat jadwal tiba dan posting gagal.
    """
    if not TOKEN or not IGID:
        print("GAGAL: IG_ACCESS_TOKEN atau IG_BUSINESS_ACCOUNT_ID belum terisi.")
        print("Isi di GitHub → Settings → Secrets and variables → Actions.")
        return 1

    def tanya(path, **p):
        p["access_token"] = TOKEN
        try:
            r = requests.get(f"{BASE}/{path}", params=p, timeout=60)
        except requests.RequestException as e:  # jaringan, bukan token
            return None, f"tidak bisa menghubungi Meta: {type(e).__name__}"
        try:
            d = r.json()
        except Exception:  # noqa: BLE001
            return None, r.text[:200]
        if r.status_code >= 400:
            return None, d.get("error", {}).get("message", str(d))[:300]
        return d, None

    # 1. Token hidup?
    me, err = tanya("me", fields="id,name")
    if err:
        print(f"GAGAL: token ditolak Meta.\n  {err}")
        print("\nBuat token baru di developers.facebook.com/tools/explorer,")
        print("perpanjang di developers.facebook.com/tools/debug/accesstoken,")
        print("lalu perbarui secret IG_ACCESS_TOKEN.")
        return 1
    print(f"Token hidup. Atas nama: {me.get('name')} (id {me.get('id')})")

    # 2. Benar-benar bisa menyentuh akun Instagram yang dipakai agent?
    ig, err = tanya(IGID, fields="id,username")
    if err:
        print(f"GAGAL: token hidup, tapi tidak berwenang atas akun Instagram {IGID}.\n  {err}")
        print("\nBiasanya karena Page 'Piringkalori' tidak ikut dicentang saat")
        print("memberi izin. Ulangi Generate Access Token, pilih Edit settings,")
        print("dan pastikan Page-nya tercentang.")
        return 1
    print(f"Akun Instagram terjangkau: @{ig.get('username')} (id {ig.get('id')})")

    # 3. Kapan habis? Ini yang bikin posting berhenti diam-diam.
    dbg, err = tanya("debug_token", input_token=TOKEN)
    if err:
        print(f"Catatan: masa berlaku tidak bisa dibaca ({err}). Tidak fatal.")
    else:
        d = dbg.get("data", {})
        exp = d.get("expires_at")
        if exp == 0:
            print("Masa berlaku: tidak kedaluwarsa.")
        elif exp:
            habis = dt.datetime.fromtimestamp(exp, TZ)
            sisa = (habis - dt.datetime.now(TZ)).days
            print(f"Masa berlaku sampai {habis:%d %B %Y} — sisa {sisa} hari.")
            if sisa < 14:
                print("  PERHATIAN: kurang dari dua minggu. Perbarui sekarang.")
        izin = d.get("scopes", [])
        wajib = ["instagram_basic", "instagram_content_publish"]
        kurang = [s for s in wajib if s not in izin]
        if kurang:
            print(f"GAGAL: izin yang kurang: {', '.join(kurang)}")
            return 1
        print(f"Izin lengkap ({len(izin)} scope, termasuk instagram_content_publish).")

    print("\nSEMUA BERES — token siap dipakai posting.")
    return 0


def cek_semua_caption() -> int:
    """Periksa panjang caption setiap konten. Kembalikan 1 kalau ada yang lewat."""
    folders = sorted((ROOT / "content").glob("*/content.json"))
    if not folders:
        print("Tidak ada konten di content/")
        return 0
    gagal = 0
    print(f"{'konten':<30}{'panjang':>9}{'sisa':>8}  status")
    for f in folders:
        nama = f.parent.name
        doc = json.loads(f.read_text(encoding="utf-8"))
        try:
            n = len(caption_of(doc))
            print(f"{nama:<30}{n:>9}{CAPTION_MAX - n:>8}  OK")
        except RuntimeError as e:  # noqa: BLE001
            gagal += 1
            print(f"{nama:<30}{'':>9}{'':>8}  LEWAT BATAS — {e}")
    print(f"\n{len(folders)} konten diperiksa, {gagal} lewat batas.")
    return 1 if gagal else 0


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tampilkan saja, jangan posting")
    ap.add_argument("--kode", help="paksa posting satu kode konten")
    ap.add_argument("--force", action="store_true", help="abaikan jadwal")
    ap.add_argument("--cek", action="store_true",
                    help="periksa panjang caption semua konten, tanpa posting")
    ap.add_argument("--cek-token", action="store_true",
                    help="periksa token Meta ke server, tanpa posting")
    a = ap.parse_args()

    if a.cek:
        sys.exit(cek_semua_caption())
    if a.cek_token:
        sys.exit(cek_token())

    rows = read_cal()
    now = dt.datetime.now(TZ)
    print(f"Sekarang (WIB): {now:%Y-%m-%d %H:%M}")

    antre = []
    for r in rows:
        if a.kode:
            if r["kode"] == a.kode and r["status"] != "posted":
                antre.append(r)
            continue
        if r.get("status") == "approved" and (a.force or due(r, now)):
            antre.append(r)

    if not antre:
        print("Tidak ada yang jatuh tempo. Selesai.")
        return

    if not a.dry_run and (not TOKEN or not IGID):
        sys.exit("IG_ACCESS_TOKEN / IG_BUSINESS_ACCOUNT_ID belum diisi. Lihat docs/SETUP.md.")

    terbit = []
    for r in antre:
        kode, tipe = r["kode"], r.get("tipe_konten", "feed_carousel")
        print(f"\n→ {kode} ({tipe}) dijadwalkan {r['tanggal_posting']} {r['jam_posting']}")
        if a.dry_run:
            doc = load_doc(kode)
            print(f"   caption {len(caption_of(doc))} karakter, "
                  f"{len(urls_for(kode,'carousel'))} slide, "
                  f"{len(urls_for(kode,'story'))} story, "
                  f"reel {'ada' if reel_url(kode) else 'BELUM ADA'}")
            if menunggu_feed(r, doc, rows):
                print("   (akan menunggu sampai feed-nya tayang dulu)")
            n = story_nomor(tipe)
            if tipe == "reel":
                daftar = [reel_url(kode)]
            elif n >= 0:
                daftar = urls_for(kode, "story")
                daftar = daftar[n - 1:n] if n else daftar
            else:
                daftar = urls_for(kode, "carousel")
            for u in daftar:
                print(f"   {u}")
            continue
        try:
            doc = load_doc(kode)
            if menunggu_feed(r, doc, rows) and not a.force:
                print("   Ditahan: feed-nya belum tayang. Dicoba lagi di putaran berikutnya.")
                continue
            res = jalankan(tipe, doc, kode)
            r.update(res, status="posted",
                     posted_at=dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), catatan="")
            print(f"   TAYANG — {res['permalink'] or res['media_id']}")
            terbit.append((kode, r, doc))
            catat_log(kode, r, doc)
        except Exception as e:  # noqa: BLE001
            r["status"] = "failed"
            r["catatan"] = str(e)[:280]
            print(f"   GAGAL: {e}")

    # Arsip dilakukan SETELAH semua baris diproses, bukan per baris.
    # Kalau satu kode punya beberapa baris (mis. feed + story), mengarsipkan
    # setelah baris pertama akan memindahkan foldernya dan membuat baris
    # berikutnya gagal dengan "folder konten tidak ditemukan".
    if not a.dry_run:
        menunggu = {"draft", "review", "approved"}
        for kode, row, doc in terbit:
            sisa = [x for x in rows if x["kode"] == kode and x.get("status") in menunggu]
            if sisa:
                print(f"\n{kode}: belum diarsipkan — masih ada "
                      f"{len(sisa)} baris yang menunggu tayang.")
                continue
            if not (ROOT / "out" / kode).exists():
                continue  # sudah diarsipkan oleh baris lain di putaran ini
            archive(kode, row, doc, rows)
            print(f"\n{kode}: diarsipkan ke archive/{dt.datetime.now(TZ):%Y-%m}/{kode}/")
        write_cal(rows)
        print("\ncalendar.csv diperbarui.")


if __name__ == "__main__":
    main()
