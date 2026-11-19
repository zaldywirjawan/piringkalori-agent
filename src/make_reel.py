#!/usr/bin/env python3
"""
PEMBUAT REEL DARI SLIDE — PIRINGKALORI
======================================
Mengubah slide carousel yang sudah dirender (out/<KODE>/carousel/*.png,
1080x1350) menjadi satu video Reel 9:16 (1080x1920):

    out/<KODE>/reel/reel.mp4

Tiap slide tampil beberapa detik dengan transisi halus. Slide ditaruh di
tengah, di atas latar versi buram dari slide itu sendiri, supaya tidak ada
bagian slide yang terpotong. Videonya diberi trek audio hening — sebagian
pemutar menolak video tanpa trek audio sama sekali.

Butuh `ffmpeg`. Pakai:
    python3 src/make_reel.py --all
    python3 src/make_reel.py R03 R04
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

W, H = 1080, 1920
FPS = 30
COVER_S = 3.0      # slide pertama: cukup untuk membaca judul
SLIDE_S = 4.0      # slide lain
FADE_S = 0.4


def build(kode: str) -> pathlib.Path | None:
    slides = sorted((ROOT / "out" / kode / "carousel").glob("*.png"))
    if len(slides) < 2:
        print(f"  {kode}: dilewat — slide carousel kurang dari 2.")
        return None
    dest = ROOT / "out" / kode / "reel" / "reel.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)

    durs = [COVER_S] + [SLIDE_S] * (len(slides) - 1)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, d in zip(slides, durs):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d + FADE_S}", "-i", str(p)]

    f = []
    for i in range(len(slides)):
        f.append(
            f"[{i}:v]split[a{i}][b{i}];"
            f"[a{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=40:2,eq=brightness=-0.06[bg{i}];"
            f"[b{i}]scale={W}:-2[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v{i}]"
        )
    last, t = "v0", 0.0
    for i in range(1, len(slides)):
        t += durs[i - 1]
        out = f"x{i}"
        f.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE_S}:offset={t:.2f}[{out}]")
        last = out
    total = sum(durs) + FADE_S

    cmd += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-filter_complex", ";".join(f), "-map", f"[{last}]", "-map", f"{len(slides)}:a",
            "-t", f"{total:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(dest)]
    subprocess.run(cmd, check=True)
    print(f"  {kode}: reel {total:.0f} detik, {dest.stat().st_size / 1e6:.1f} MB "
          f"→ {dest.relative_to(ROOT)}")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kode", nargs="*")
    ap.add_argument("--all", action="store_true", help="semua konten di out/")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg belum terpasang.")
    kodes = (sorted(p.name for p in (ROOT / "out").iterdir() if p.is_dir())
             if a.all else a.kode)
    if not kodes:
        sys.exit("Sebutkan kode konten atau pakai --all.")
    print(f"Membuat reel untuk {len(kodes)} konten…")
    for k in kodes:
        build(k)


if __name__ == "__main__":
    main()
