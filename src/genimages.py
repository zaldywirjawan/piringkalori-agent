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
import json
import os
import pathlib
import sys
import time

import requests

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

def gen_gemini(prompt: str, aspect: str, model: str) -> bytes:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY belum diisi. Lihat docs/SETUP.md bagian 3.")
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    body = {
        "model": model,
        "input": [{"type": "text", "text": prompt}],
        "response_format": {
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": aspect,
            "image_size": "1K",
        },
    }
    r = requests.post(url, json=body, timeout=TIMEOUT,
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    if r.status_code == 400 and "aspect_ratio" in r.text:
        body["response_format"].pop("aspect_ratio")
        r = requests.post(url, json=body, timeout=TIMEOUT,
                          headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    r.raise_for_status()
    data = r.json()
    b64 = (data.get("interaction", {}).get("output_image", {}) or {}).get("data")
    if not b64:  # bentuk respons lama (generateContent)
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    b64 = part["inlineData"]["data"]
    if not b64:
        raise RuntimeError(f"Respons tidak berisi gambar: {json.dumps(data)[:400]}")
    return base64.b64decode(b64)


# --------------------------------------------------------------------------
# provider: openai
# --------------------------------------------------------------------------

OPENAI_SIZES = {"1:1": "1024x1024", "4:5": "1024x1536", "2:3": "1024x1536",
                "9:16": "1024x1536", "3:2": "1536x1024", "16:9": "1536x1024"}


def gen_openai(prompt: str, aspect: str, model: str) -> bytes:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY belum diisi. Lihat docs/SETUP.md bagian 3.")
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
                dest.write_bytes(generate(prompt, aspect))
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
