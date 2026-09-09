#!/usr/bin/env python3
"""
GENERATOR FOTO MAKANAN AI — PIRINGKALORI
========================================
Membaca daftar `images` di content.json, lalu membuat foto makanan pakai API
image generator. Hasil disimpan di content/<FOLDER>/img/<id>.png dan otomatis
dipakai oleh render.py.

Kunci API dibaca dari environment variable (JANGAN ditulis di file):
    IMAGE_PROVIDER   -> "gemini" (default) atau "openai"
    GEMINI_API_KEY   -> kalau provider gemini
    OPENAI_API_KEY   -> kalau provider openai

Pakai:
    python3 src/genimages.py content/R01_rendang-ayam/content.json
    python3 src/genimages.py --all
    python3 src/genimages.py --all --force     # timpa gambar yang sudah ada

Gambar yang sudah ada TIDAK dibuat ulang (hemat biaya), kecuali pakai --force.
"""

import argparse
import base64
import io
import json
import os
import pathlib
import sys
import time

import requests
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))

# Gaya visual yang ditempel ke SEMUA prompt supaya satu carousel terasa satu set.
STYLE_SUFFIX = (
    "Photorealistic food photography, natural soft daylight from the left, "
    "shallow depth of field, clean minimal composition, warm cream background "
    "(#FDF8F0), matte ceramic tableware, fresh Indonesian home-cooking styling, "
    "no text, no watermark, no hands, no logo, appetizing but honest portion size."
)

TIMEOUT = 180


# --------------------------------------------------------------------------
# provider: gemini
# --------------------------------------------------------------------------

def _ambil_gambar(data: dict) -> str:
    """Cari data base64 gambar di dalam respons, apa pun bentuknya."""
    for step in data.get("steps", []) or []:
        for c in step.get("content", []) or []:
            if c.get("type") == "image" and c.get("data"):
                return c["data"]
    oi = (data.get("interaction", {}) or {}).get("output_image") or {}
    if oi.get("data"):
        return oi["data"]
    if (data.get("output_image") or {}).get("data"):
        return data["output_image"]["data"]
    for cand in data.get("candidates", []) or []:
        for part in (cand.get("content", {}) or {}).get("parts", []) or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return inline["data"]
    return ""


def gen_gemini(prompt: str, aspect: str, model: str) -> bytes:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY belum diisi. Lihat docs/SETUP.md bagian 4.")
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    dasar = {"model": model, "input": [{"type": "text", "text": prompt}]}

    varian = [
        {**dasar, "response_format": {"type": "image", "mime_type": "image/jpeg",
                                      "aspect_ratio": aspect, "image_size": "1K"}},
        {**dasar, "response_format": {"type": "image", "aspect_ratio": aspect}},
        {**dasar, "response_format": {"type": "image", "image_size": "1K"}},
        {**dasar, "response_format": {"type": "image"}},
        dasar,
    ]

    galat = []
    for body in varian:
        r = requests.post(url, json=body, timeout=TIMEOUT, headers=headers)
        if r.ok:
            b64 = _ambil_gambar(r.json())
            if b64:
                return base64.b64decode(b64)
            galat.append(f"200 tapi tanpa gambar: {json.dumps(r.json())[:200]}")
            continue
        try:
            pesan = r.json().get("error", {}).get("message", r.text)[:220]
        except Exception:  # noqa: BLE001
            pesan = r.text[:220]
        galat.append(f"{r.status_code}: {pesan}")
        if r.status_code in (401, 403):
            break

    raise RuntimeError(" | ".join(dict.fromkeys(galat)))


# --------------------------------------------------------------------------
# provider: openai
# --------------------------------------------------------------------------

OPENAI_SIZES = {"1:1": "1024x1024", "4:5": "1024x1536", "2:3": "1024x1536",
                "9:16": "1024x1536", "3:2": "1536x1024", "16:9": "1536x1024"}


def gen_openai(prompt: str, aspect: str, model: str) -> bytes:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY belum diisi. Lihat docs/SETUP.md bagian 4.")
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model or "gpt-image-1", "prompt": prompt,
              "size": OPENAI_SIZES.get(aspect, "1024x1536"), "n": 1},
        timeout=TIMEOUT)
    r.raise_for_status()
    return base64.b64decode(r.json()["data"][0]["b64_json"])


# --------------------------------------------------------------------------

def generate(prompt: str, aspect: str) -> bytes:
    provider = os.environ.get("IMAGE_PROVIDER", "gemini").lower()
    model = os.environ.get("IMAGE_MODEL", "")
    if provider == "openai":
        return gen_openai(prompt, aspect, model or "gpt-image-1")
    return gen_gemini(prompt, aspect, model or "gemini-3.1-flash-image")


def process(path: pathlib.Path, force: bool) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))
    imgs = doc.get("images", [])
    if not imgs:
        print(f"  {doc['kode']}: tidak ada foto yang perlu dibuat.")
        return 0

    outdir = path.parent / "img"
    outdir.mkdir(exist_ok=True)
    made = 0
    for spec in imgs:
        dest = outdir / f"{spec['id']}.png"
        if dest.exists() and not force:
            print(f"  {doc['kode']}/{spec['id']}: sudah ada, dilewati.")
            continue
        prompt = f"{spec['prompt'].strip().rstrip('.')}. {STYLE_SUFFIX}"
        aspect = spec.get("aspect", "4:5")
        for attempt in range(1, 4):
            try:
                Image.open(io.BytesIO(generate(prompt, aspect))).convert("RGB").save(dest, "PNG")
                print(f"  {doc['kode']}/{spec['id']}: dibuat ({dest.stat().st_size // 1024} KB)")
                made += 1
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    print(f"  {doc['kode']}/{spec['id']}: GAGAL — {e}")
                else:
                    time.sleep(4 * attempt)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    targets = ([p for p in sorted((ROOT / "content").glob("*/content.json"))]
               if a.all else [pathlib.Path(p) for p in a.paths])
    if not targets:
        sys.exit("Sebutkan path content.json atau pakai --all.")

    total = 0
    print(f"Provider: {os.environ.get('IMAGE_PROVIDER', 'gemini')}")
    for t in targets:
        total += process(t, a.force)
    print(f"Selesai. {total} gambar baru dibuat.")


if __name__ == "__main__":
    main()
