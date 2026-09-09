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


def publish_container(cid: str) -> dict:
    wait_ready(cid)
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


def post_story(doc: dict, kode: str) -> dict:
    urls = urls_for(kode, "story")
    if not urls:
        raise RuntimeError("Tidak ada gambar story untuk diposting.")
    out = []
    for u in urls:
        out.append(publish_container(make_container(image_url=u, media_type="STORIES")))
        time.sleep(2)
    return {"media_id": ",".join(o["media_id"] for o in out),
            "permalink": out[0]["permalink"]}


HANDLERS = {"feed_carousel": post_carousel, "feed_single": post_single, "story": post_story}


def caption_of(doc: dict) -> str:
    cap = doc.get("caption", "")
    if doc.get("disclosure_ai"):
        cap += "\n\n" + json.loads(
            (ROOT / "brand" / "tokens.json").read_text(encoding="utf-8")
        )["disclosure_ai"]
    return cap


# --------------------------------------------------------------------------
# arsip + log
# --------------------------------------------------------------------------

def archive(kode: str, row: dict, doc: dict):
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
    }, ensure_ascii=False, indent=2), encoding="utf-8")

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tampilkan saja, jangan posting")
    ap.add_argument("--kode", help="paksa posting satu kode konten")
    ap.add_argument("--force", action="store_true", help="abaikan jadwal")
    a = ap.parse_args()

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

    for r in antre:
        kode, tipe = r["kode"], r.get("tipe_konten", "feed_carousel")
        print(f"\n→ {kode} ({tipe}) dijadwalkan {r['tanggal_posting']} {r['jam_posting']}")
        if a.dry_run:
            doc = load_doc(kode)
            print(f"   caption {len(caption_of(doc))} karakter, "
                  f"{len(urls_for(kode,'carousel'))} slide, "
                  f"{len(urls_for(kode,'story'))} story")
            for u in urls_for(kode, tipe.replace("feed_carousel", "carousel")
                                          .replace("feed_single", "carousel")):
                print(f"   {u}")
            continue
        try:
            doc = load_doc(kode)
            res = HANDLERS[tipe](doc, kode)
            r.update(res, status="posted",
                     posted_at=dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), catatan="")
            print(f"   TAYANG — {res['permalink'] or res['media_id']}")

            tags = doc.get("hashtags", "")
            if tags and tipe != "story":
                time.sleep(3)
                try:
                    api("POST", f"{res['media_id']}/comments", message=tags)
                    print("   hashtag ditaruh di komentar pertama.")
                except Exception as e:  # noqa: BLE001
                    r["catatan"] = f"hashtag gagal: {e}"
                    print(f"   hashtag GAGAL: {e}")

            archive(kode, r, doc)
            print(f"   diarsipkan ke archive/{dt.datetime.now(TZ):%Y-%m}/{kode}/")
        except Exception as e:  # noqa: BLE001
            r["status"] = "failed"
            r["catatan"] = str(e)[:280]
            print(f"   GAGAL: {e}")

    if not a.dry_run:
        write_cal(rows)
        print("\ncalendar.csv diperbarui.")


if __name__ == "__main__":
    main()
