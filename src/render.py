#!/usr/bin/env python3
"""
RENDERER PIRINGKALORI
=====================
Mengubah `content.json` menjadi file PNG siap posting:
  - carousel : 1080 x 1350 (rasio 4:5)
  - story    : 1080 x 1920 (rasio 9:16)

Pakai:
    python3 src/render.py content/L01_kesalahan-diet/content.json
    python3 src/render.py --all

Hasil masuk ke: out/<KODE>/carousel/01.png ... dan out/<KODE>/story/01.png ...

Tidak butuh internet. Semua font sudah ada di brand/fonts/.
"""

import argparse
import html
import json
import pathlib
import shutil
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))
C = TOKENS["colors"]
CANVAS = TOKENS["canvas"]


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------

def base_css(w: int, h: int) -> str:
    return f"""
@font-face {{ font-family:'Poppins'; src:url('brand/fonts/poppins-latin-400-normal.woff2') format('woff2'); font-weight:400; }}
@font-face {{ font-family:'Poppins'; src:url('brand/fonts/poppins-latin-500-normal.woff2') format('woff2'); font-weight:500; }}
@font-face {{ font-family:'Poppins'; src:url('brand/fonts/poppins-latin-600-normal.woff2') format('woff2'); font-weight:600; }}
@font-face {{ font-family:'Poppins'; src:url('brand/fonts/poppins-latin-700-normal.woff2') format('woff2'); font-weight:700; }}
@font-face {{ font-family:'Fraunces'; src:url('brand/fonts/fraunces-latin-400-italic.woff2') format('woff2'); font-weight:400; font-style:italic; }}
@font-face {{ font-family:'Fraunces'; src:url('brand/fonts/fraunces-latin-600-italic.woff2') format('woff2'); font-weight:600; font-style:italic; }}

* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{w}px; height:{h}px; }}
body {{
  font-family:'Poppins',sans-serif;
  -webkit-font-smoothing:antialiased;
  color:{C['charcoal']};
  overflow:hidden;
}}
.slide {{
  position:relative; width:{w}px; height:{h}px;
  display:flex; flex-direction:column;
  padding:80px; overflow:hidden;
}}
.slide.story {{ padding:230px 80px 300px; }}
.bg-krem {{ background:{C['krem']}; }}
.bg-sage {{ background:{C['sage']}; color:{C['krem']}; }}
.bg-coral {{ background:{C['coral']}; color:#fff; }}

/* header --------------------------------------------------------------- */
.head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:24px; }}
.badge {{
  font-size:26px; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
  padding:16px 28px; border-radius:999px; white-space:nowrap;
}}
.badge-kat {{ background:{C['krem']}; color:{C['sage']}; }}
.bg-krem .badge-kat {{ background:{C['sageSoft']}; color:{C['sage']}; }}
.badge-kal {{ background:{C['coral']}; color:#fff; letter-spacing:.06em; }}

/* typography ----------------------------------------------------------- */
.headline {{ font-weight:700; line-height:1.06; letter-spacing:-.02em; }}
.rule {{ width:128px; height:12px; border-radius:999px; background:{C['coral']}; margin:40px 0 34px; }}
.subline {{ font-size:36px; line-height:1.42; font-weight:400; opacity:.88; }}
.title {{ font-size:56px; font-weight:700; line-height:1.14; color:{C['sage']}; letter-spacing:-.015em; }}
.bg-sage .title {{ color:{C['krem']}; }}
.eyebrow {{ font-size:26px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:{C['coral']}; margin-bottom:18px; }}
.accent {{ font-family:'Fraunces',serif; font-style:italic; font-weight:600; }}
.grow {{ flex:1 1 auto; min-height:0; }}
/* Teks langkah tidak boleh dikompres: fotonya yang mengalah. */
.keep {{ flex:0 0 auto; }}
.photo.flexy {{ min-height:320px; }}
.mid {{ flex:1 1 auto; min-height:0; display:flex; flex-direction:column; justify-content:center; }}

/* footer --------------------------------------------------------------- */
.foot {{
  display:flex; justify-content:space-between; align-items:center;
  font-size:26px; font-weight:500; letter-spacing:.02em; opacity:.72;
}}
.foot .mark b {{ font-weight:700; }}
.dots {{ display:flex; gap:10px; align-items:center; }}
.dot {{ width:12px; height:12px; border-radius:999px; background:currentColor; opacity:.3; }}
.dot.on {{ opacity:1; width:34px; }}

/* photo card ----------------------------------------------------------- */
.photo {{
  border-radius:44px; overflow:hidden; background:{C['sageSoft']};
  position:relative; width:100%; flex:1 1 auto; min-height:0;
}}
/* Foto dipasang absolut supaya tingginya TIDAK ikut menghitung tinggi kotak.
   Kalau ikut menghitung, gambar 1024x1536 memaksa kotaknya jadi ~1400px dan
   mendorong teks di bawahnya keluar kanvas. Dengan absolut, kotak foto hanya
   mengambil sisa ruang yang benar-benar tersedia. */
.photo img {{ position:absolute; inset:0; width:100%; height:100%;
              object-fit:cover; display:block; }}
.photo.ph::after {{
  content:'FOTO BELUM ADA'; position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  font-size:30px; font-weight:600; letter-spacing:.18em; color:{C['sage']}; opacity:.5;
}}

/* compare table -------------------------------------------------------- */
.cmp {{ width:100%; border-collapse:separate; border-spacing:0 14px; }}
.cmp th {{ font-size:28px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; padding:0 22px 12px; }}
.cmp th.l {{ text-align:left; color:{C['muted']}; }}
.cmp th.b {{ color:{C['muted']}; text-align:center; }}
.cmp th.d {{ color:{C['sage']}; text-align:center; }}
.cmp td {{ font-size:34px; padding:24px 22px; background:#fff; }}
.cmp td.lbl {{ font-weight:500; border-radius:22px 0 0 22px; }}
.cmp td.b {{ text-align:center; color:{C['muted']}; text-decoration:line-through; text-decoration-color:{C['coral']}; text-decoration-thickness:3px; }}
.cmp td.d {{ text-align:center; font-weight:700; color:{C['sage']}; background:{C['sageSoft']}; border-radius:0 22px 22px 0; }}
.note {{ font-size:23px; line-height:1.5; color:{C['muted']}; margin-top:26px; }}

/* macro bars ----------------------------------------------------------- */
.macro {{ margin-bottom:30px; }}
.macro-top {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:12px; }}
.macro-lbl {{ font-size:32px; font-weight:500; }}
.macro-val {{ font-size:32px; font-weight:700; color:{C['sage']}; }}
.bar {{ height:26px; border-radius:999px; background:{C['kremDeep']}; overflow:hidden; }}
.bar span {{ display:block; height:100%; border-radius:999px; background:{C['sage']}; }}
.bar.hi span {{ background:{C['coral']}; }}
.porsi {{
  display:inline-block; font-size:27px; font-weight:600; color:{C['sage']};
  background:{C['sageSoft']}; padding:14px 26px; border-radius:999px; margin-bottom:34px;
  align-self:flex-start;
}}

/* numbered list -------------------------------------------------------- */
.item {{ display:flex; gap:30px; margin-bottom:38px; }}
.num {{
  flex:0 0 auto; width:66px; height:66px; border-radius:999px;
  background:{C['coral']}; color:#fff; font-size:34px; font-weight:700;
  display:flex; align-items:center; justify-content:center;
}}
.bg-sage .num {{ background:{C['krem']}; color:{C['sage']}; }}
.item-h {{ font-size:38px; font-weight:700; line-height:1.24; margin-bottom:10px; }}
.item-b {{ font-size:29px; line-height:1.5; opacity:.82; }}

/* step list (compact) --------------------------------------------------- */
.step {{ display:flex; gap:22px; align-items:flex-start; margin-bottom:22px; }}
.step .num {{ width:48px; height:48px; font-size:26px; }}
.step-t {{ font-size:29px; line-height:1.45; padding-top:6px; }}

/* callout chips --------------------------------------------------------- */
.chips {{ display:flex; flex-wrap:wrap; gap:16px; margin-top:32px; }}
.chip {{
  font-size:27px; font-weight:500; padding:16px 26px; border-radius:999px;
  background:#fff; border:3px solid {C['sageSoft']};
}}
.chip b {{ color:{C['sage']}; font-weight:700; }}

/* body text ------------------------------------------------------------- */
.body {{ font-size:33px; line-height:1.55; }}
.body p {{ margin-bottom:26px; }}
.body p:last-child {{ margin-bottom:0; }}

/* quote ----------------------------------------------------------------- */
.quote {{ font-family:'Fraunces',serif; font-style:italic; font-weight:600; font-size:64px; line-height:1.28; }}

/* cta ------------------------------------------------------------------- */
.cta-pill {{
  display:inline-block; background:{C['coral']}; color:#fff; font-size:34px; font-weight:600;
  padding:26px 46px; border-radius:999px; margin-top:34px;
}}

/* story extras ---------------------------------------------------------- */
.story .headline {{ line-height:1.1; }}
.sticker-hint {{
  margin-top:auto; font-size:25px; font-weight:500; opacity:.7;
  border-top:3px solid currentColor; padding-top:22px;
}}
"""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def rich(x) -> str:
    """Izinkan **tebal** dan *miring aksen* di dalam teks konten."""
    s = esc(x)
    out, bold = [], False
    i = 0
    while i < len(s):
        if s.startswith("**", i):
            out.append("</b>" if bold else "<b>")
            bold = not bold
            i += 2
        else:
            out.append(s[i])
            i += 1
    if bold:
        out.append("</b>")
    return "".join(out)


def photo_html(src, base: pathlib.Path) -> str:
    if not src:
        return '<div class="photo ph"></div>'
    p = (base / src) if not str(src).startswith(("http://", "https://")) else None
    if p is not None and not p.exists():
        return '<div class="photo ph"></div>'
    url = str(src) if p is None else p.relative_to(ROOT).as_posix()
    return f'<div class="photo"><img src="{esc(url)}"></div>'


def foot(idx: int, total: int, hint: str = "geser →") -> str:
    dots = "".join(
        f'<span class="dot{" on" if i == idx else ""}"></span>' for i in range(total)
    )
    return (
        f'<div class="foot"><span class="mark"><b>piring</b>kalori</span>'
        f'<span class="dots">{dots}</span>'
        f'<span>{esc(hint) if idx < total - 1 else "simpan ♡"}</span></div>'
    )


def head(kat: str = None, kal: str = None) -> str:
    left = f'<span class="badge badge-kat">{esc(kat)}</span>' if kat else "<span></span>"
    right = f'<span class="badge badge-kal">{esc(kal)}</span>' if kal else "<span></span>"
    return f'<div class="head">{left}{right}</div>'


# --------------------------------------------------------------------------
# slide builders — satu fungsi per tipe slide
# --------------------------------------------------------------------------

def s_cover(s, ctx):
    kat = s.get("badge_kategori") or ctx["kat_label"]
    kal = s.get("badge_kalori")
    img = s.get("image")
    sub = f'<div class="subline">{rich(s["subline"])}</div>' if s.get("subline") else ""
    block = (f'<div class="headline fit" data-max="104" data-min="52">{rich(s["headline"])}</div>'
             f'<div class="rule"></div>{sub}')
    if img:
        mid = (f'<div style="height:56px"></div>{block}<div style="height:34px"></div>'
               f'{photo_html(img, ctx["base"])}<div style="height:34px"></div>')
    else:
        mid = f'<div class="mid">{block}</div>'
    return f"""<div class="slide bg-sage">
  {head(kat, kal)}
  {mid}
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_compare(s, ctx):
    rows = "".join(
        f'<tr><td class="lbl">{rich(r["label"])}</td>'
        f'<td class="b">{esc(r["biasa"])}</td>'
        f'<td class="d">{esc(r["diet"])}</td></tr>'
        for r in s.get("rows", [])
    )
    note = f'<div class="note">{rich(s["catatan"])}</div>' if s.get("catatan") else ""
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div class="mid fitbox">
    <div class="title">{rich(s.get('judul','Biasa vs Versi Diet'))}</div>
    <div style="height:36px"></div>
    <table class="cmp"><thead><tr>
      <th class="l">Per porsi</th><th class="b">{esc(s.get('kolom',['Biasa','Diet'])[0])}</th>
      <th class="d">{esc(s.get('kolom',['Biasa','Diet'])[1])}</th>
    </tr></thead><tbody>{rows}</tbody></table>
    {note}
  </div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_photo_callout(s, ctx):
    chips = "".join(f'<span class="chip">{rich(c)}</span>' for c in s.get("callouts", []))
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div style="height:40px"></div>
  <div class="title">{rich(s.get('judul','Bahan'))}</div>
  <div style="height:32px"></div>
  {photo_html(s.get('image'), ctx['base'])}
  <div class="chips">{chips}</div>
  <div style="height:34px"></div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_steps(s, ctx):
    steps = "".join(
        f'<div class="step"><div class="num">{i+1}</div><div class="step-t">{rich(t)}</div></div>'
        for i, t in enumerate(s.get("steps", []))
    )
    # Kalau ada foto, fotolah yang mengalah saat ruang sempit (kelas `flexy`),
    # dan daftar langkah dikunci setinggi isinya (`keep`) supaya tidak ada
    # langkah yang terpotong. Tanpa foto, daftar langkah yang mengisi ruang.
    if s.get("image"):
        photo = (photo_html(s["image"], ctx["base"]).replace(
            'class="photo"', 'class="photo flexy"', 1)
            + '<div style="height:30px"></div>')
        kelas = "keep"
    else:
        photo, kelas = "", "grow"
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div style="height:40px"></div>
  <div class="title">{rich(s.get('judul','Cara Masak'))}</div>
  <div style="height:30px"></div>
  {photo}
  <div class="{kelas}">{steps}</div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_macros(s, ctx):
    items = s.get("items", [])
    mx = max([float(it.get("value", 0)) for it in items] or [1]) or 1
    bars = ""
    for it in items:
        pct = float(it.get("pct", 100 * float(it.get("value", 0)) / mx))
        hi = " hi" if it.get("highlight") else ""
        bars += (
            f'<div class="macro"><div class="macro-top">'
            f'<span class="macro-lbl">{esc(it["label"])}</span>'
            f'<span class="macro-val">{esc(it["value"])}{esc(it.get("unit",""))}</span></div>'
            f'<div class="bar{hi}"><span style="width:{max(4,min(100,pct)):.1f}%"></span></div></div>'
        )
    porsi = f'<div class="porsi">{esc(s["porsi"])}</div>' if s.get("porsi") else ""
    note = f'<div class="note">{rich(s["catatan"])}</div>' if s.get("catatan") else ""
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div class="mid fitbox">
    <div class="title">{rich(s.get('judul','Rincian Gizi'))}</div>
    <div style="height:30px"></div>
    {porsi}
    <div>{bars}{note}</div>
  </div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_list(s, ctx):
    items = "".join(
        f'<div class="item"><div class="num">{i+1}</div><div>'
        f'<div class="item-h">{rich(it["headline"])}</div>'
        + (f'<div class="item-b">{rich(it["body"])}</div>' if it.get("body") else "")
        + "</div></div>"
        for i, it in enumerate(s.get("items", []))
    )
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div class="mid fitbox">
    <div class="title">{rich(s.get('judul',''))}</div>
    <div style="height:40px"></div>
    <div>{items}</div>
  </div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_text(s, ctx):
    paras = "".join(f"<p>{rich(p)}</p>" for p in s.get("body", []))
    eyebrow = f'<div class="eyebrow">{esc(s["eyebrow"])}</div>' if s.get("eyebrow") else ""
    return f"""<div class="slide bg-krem">
  {head(ctx['kat_label'])}
  <div class="mid fitbox">
    {eyebrow}
    <div class="title">{rich(s.get('judul',''))}</div>
    <div style="height:34px"></div>
    <div class="body">{paras}</div>
  </div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_quote(s, ctx):
    at = f'<div class="subline" style="margin-top:38px">{rich(s["attrib"])}</div>' if s.get("attrib") else ""
    return f"""<div class="slide bg-sage">
  {head(ctx['kat_label'])}
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    <div class="quote fit" data-max="72" data-min="40">{rich(s['text'])}</div>{at}
  </div>
  {foot(ctx['i'], ctx['n'])}
</div>"""


def s_cta(s, ctx):
    sub = f'<div class="subline" style="margin-top:26px">{rich(s["subtext"])}</div>' if s.get("subtext") else ""
    pill = f'<div><span class="cta-pill">{rich(s["pill"])}</span></div>' if s.get("pill") else ""
    ftr = f'<div class="note" style="color:inherit;opacity:.62;margin-top:34px">{rich(s["footer"])}</div>' if s.get("footer") else ""
    return f"""<div class="slide bg-sage">
  {head(ctx['kat_label'])}
  <div class="grow" style="display:flex;flex-direction:column;justify-content:center">
    <div class="headline fit" data-max="86" data-min="46">{rich(s['headline'])}</div>
    <div class="rule"></div>
    {sub}{pill}{ftr}
  </div>
  {foot(ctx['i'], ctx['n'], '')}
</div>"""


# story --------------------------------------------------------------------

def st_generic(s, ctx):
    bg = "bg-sage" if s.get("style", "sage") == "sage" else "bg-krem"
    eyebrow = f'<div class="eyebrow">{esc(s["eyebrow"])}</div>' if s.get("eyebrow") else ""
    sub = f'<div class="subline" style="margin-top:30px">{rich(s["subline"])}</div>' if s.get("subline") else ""
    hint = f'<div class="sticker-hint">{rich(s["sticker_hint"])}</div>' if s.get("sticker_hint") else ""
    block = (f'{eyebrow}<div class="headline fit" data-max="94" data-min="46">{rich(s["headline"])}</div>'
             f'<div class="rule"></div>{sub}')
    if s.get("image"):
        mid = f'{block}<div style="height:44px"></div>{photo_html(s.get("image"), ctx["base"])}'
    else:
        mid = f'<div class="mid">{block}</div>'
    return f"""<div class="slide story {bg}">
  {mid}
  {hint}
  <div style="height:30px"></div>
  <div class="foot"><span class="mark"><b>piring</b>kalori</span><span>{esc(s.get('cta',''))}</span></div>
</div>"""


BUILDERS = {
    "cover": s_cover, "compare": s_compare, "photo_callout": s_photo_callout,
    "steps": s_steps, "macros": s_macros, "list": s_list, "text": s_text,
    "quote": s_quote, "cta": s_cta,
}

FIT_JS = """() => {
  document.querySelectorAll('.fit').forEach(el => {
    const max = +(el.dataset.max || 80), min = +(el.dataset.min || 32);
    let size = max;
    el.style.fontSize = size + 'px';
    const room = () => el.parentElement.clientHeight;
    while (size > min && el.scrollHeight > room() * 0.62) {
      size -= 2; el.style.fontSize = size + 'px';
    }
  });
  document.querySelectorAll('.fitbox').forEach(box => {
    let scale = 100;
    while (scale > 62 && box.scrollHeight > box.clientHeight) {
      scale -= 2;
      box.style.fontSize = scale + '%';
    }
  });
}"""


def render_one(page, doc_html: str, w: int, h: int, dest: pathlib.Path):
    tmp = ROOT / ".render_tmp.html"
    tmp.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><style>{base_css(w, h)}</style>"
        f"</head><body>{doc_html}</body></html>", encoding="utf-8")
    page.set_viewport_size({"width": w, "height": h})
    page.goto(tmp.as_uri())
    page.evaluate(FIT_JS)
    page.wait_for_timeout(120)
    dest.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(dest))


def render_content(path: pathlib.Path, page) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    kode = doc["kode"]
    kat = TOKENS["kategori"].get(doc.get("kategori", "resep"), {"label": ""})["label"]
    outdir = ROOT / "out" / kode
    if outdir.exists():
        shutil.rmtree(outdir)

    made = {"carousel": [], "story": []}

    slides = doc.get("carousel", [])
    for i, s in enumerate(slides):
        b = BUILDERS.get(s.get("type"))
        if not b:
            raise SystemExit(f"[{kode}] tipe slide tidak dikenal: {s.get('type')}")
        ctx = {"i": i, "n": len(slides), "kat_label": kat, "base": base}
        dest = outdir / "carousel" / f"{i+1:02d}.png"
        render_one(page, b(s, ctx), CANVAS["carousel"]["w"], CANVAS["carousel"]["h"], dest)
        made["carousel"].append(dest.relative_to(ROOT).as_posix())

    for i, s in enumerate(doc.get("story", [])):
        ctx = {"i": i, "n": 1, "kat_label": kat, "base": base}
        dest = outdir / "story" / f"{i+1:02d}.png"
        render_one(page, st_generic(s, ctx), CANVAS["story"]["w"], CANVAS["story"]["h"], dest)
        made["story"].append(dest.relative_to(ROOT).as_posix())

    (outdir / "manifest.json").write_text(json.dumps({
        "kode": kode, "slug": doc.get("slug"), "judul": doc.get("judul"),
        "kategori": doc.get("kategori"), "files": made,
        "alt_text": doc.get("alt_text", []),
        "jadwal": doc.get("jadwal", {}),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  {kode}: {len(made['carousel'])} slide carousel, {len(made['story'])} story")
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="path ke content.json")
    ap.add_argument("--all", action="store_true", help="render semua konten")
    a = ap.parse_args()

    targets = ([p for p in sorted((ROOT / "content").glob("*/content.json"))]
               if a.all else [pathlib.Path(p) for p in a.paths])
    if not targets:
        sys.exit("Tidak ada content.json yang dirender. Pakai --all atau sebutkan path-nya.")

    print(f"Merender {len(targets)} konten…")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        for t in targets:
            render_content(t, page)
        browser.close()
    tmp = ROOT / ".render_tmp.html"
    if tmp.exists():
        tmp.unlink()
    print("Selesai. Cek folder out/")


if __name__ == "__main__":
    main()
