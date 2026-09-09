#!/usr/bin/env python3
"""
Membuat halaman preview (satu file HTML mandiri) berisi semua konten yang
statusnya belum `posted`, lengkap dengan slide, caption, hashtag, dan jadwal —
untuk dilihat & disetujui dari HP.

    python3 src/build_preview.py            # semua yang belum posted
    python3 src/build_preview.py --out preview.html
"""

import argparse
import base64
import csv
import html
import io
import json
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOK = json.loads((ROOT / "brand" / "tokens.json").read_text(encoding="utf-8"))


def b64(path: pathlib.Path, width: int) -> str:
    im = Image.open(path).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def esc(x) -> str:
    return html.escape(str(x or ""))


def collect() -> list:
    rows = list(csv.DictReader((ROOT / "calendar.csv").open(encoding="utf-8")))
    by_kode: dict = {}
    for r in rows:
        if r["status"] == "posted":
            continue
        by_kode.setdefault(r["kode"], []).append(r)

    items = []
    for kode, rs in by_kode.items():
        folder = next((ROOT / "content").glob(f"{kode}_*"), None)
        if not folder:
            continue
        doc = json.loads((folder / "content.json").read_text(encoding="utf-8"))
        car = sorted((ROOT / "out" / kode / "carousel").glob("*.png"))
        sto = sorted((ROOT / "out" / kode / "story").glob("*.png"))
        items.append({"kode": kode, "doc": doc, "rows": rs,
                      "carousel": [b64(p, 500) for p in car],
                      "story": [b64(p, 330) for p in sto]})
    return items


CSS = """
:root{
  --ground:#F7F6F2; --panel:#FFFFFF; --line:#E2E5DF; --line-soft:#EDEFEA;
  --ink:#22261F; --ink-2:#5B6157; --ink-3:#8A9083;
  --sage:#2E7D5B; --sage-soft:#E4EFE8; --coral:#D9502F; --coral-soft:#FBE7E0;
  --shadow:0 1px 2px rgba(34,38,31,.05), 0 8px 24px -12px rgba(34,38,31,.18);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#14170F; --panel:#1C2018; --line:#2E3429; --line-soft:#242A20;
    --ink:#EDEFE7; --ink-2:#A9B0A2; --ink-3:#7B8377;
    --sage:#6BBF93; --sage-soft:#1E3128; --coral:#F0846A; --coral-soft:#33211B;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px -14px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --ground:#14170F; --panel:#1C2018; --line:#2E3429; --line-soft:#242A20;
  --ink:#EDEFE7; --ink-2:#A9B0A2; --ink-3:#7B8377;
  --sage:#6BBF93; --sage-soft:#1E3128; --coral:#F0846A; --coral-soft:#33211B;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px -14px rgba(0,0,0,.7);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:'Public Sans',ui-sans-serif,system-ui,sans-serif;
  font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px; margin:0 auto; padding:40px 22px 96px}

/* header */
header{border-bottom:1px solid var(--line); padding-bottom:28px; margin-bottom:38px}
.kicker{
  font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:11.5px;
  letter-spacing:.2em; text-transform:uppercase; color:var(--ink-3); margin:0 0 12px;
}
h1{
  font-family:'Fraunces',Georgia,serif; font-weight:600; font-size:clamp(30px,5.2vw,42px);
  line-height:1.14; margin:0 0 14px; letter-spacing:-.015em; text-wrap:balance;
}
.lede{color:var(--ink-2); max-width:62ch; margin:0}
.tally{display:flex; flex-wrap:wrap; gap:10px; margin-top:22px}
.tally b{
  font-family:'IBM Plex Mono',monospace; font-size:12.5px; font-weight:600;
  letter-spacing:.04em; padding:7px 13px; border-radius:7px;
  background:var(--panel); border:1px solid var(--line); color:var(--ink-2);
}
.tally b span{color:var(--ink)}

/* card */
.card{
  background:var(--panel); border:1px solid var(--line); border-radius:14px;
  box-shadow:var(--shadow); margin-bottom:30px; overflow:hidden;
}
.card-top{
  display:flex; flex-wrap:wrap; gap:14px 20px; align-items:baseline;
  padding:22px 24px; border-bottom:1px solid var(--line-soft);
}
.kode{
  font-family:'IBM Plex Mono',monospace; font-size:12.5px; font-weight:600;
  letter-spacing:.09em; padding:5px 10px; border-radius:6px;
  background:var(--sage-soft); color:var(--sage);
}
h2{font-family:'Fraunces',Georgia,serif; font-weight:600; font-size:23px; margin:0; letter-spacing:-.01em; flex:1 1 240px}
.pill{
  font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600;
  letter-spacing:.13em; text-transform:uppercase; padding:6px 11px; border-radius:999px;
  border:1px solid currentColor;
}
.pill.draft{color:var(--coral); background:var(--coral-soft)}
.pill.review{color:var(--coral); background:var(--coral-soft)}
.pill.approved{color:var(--sage); background:var(--sage-soft)}

/* meta grid */
.meta{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:1px; background:var(--line-soft); border-bottom:1px solid var(--line-soft);
}
.meta div{background:var(--panel); padding:15px 24px}
.meta dt{
  font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 5px;
}
.meta dd{margin:0; font-size:15px; font-variant-numeric:tabular-nums}

/* filmstrip */
.strip-head{
  display:flex; justify-content:space-between; align-items:baseline;
  padding:22px 24px 12px; gap:16px;
}
.strip-head h3{
  font-size:13px; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  color:var(--ink-2); margin:0;
}
.hint{font-size:13px; color:var(--ink-3)}
.strip{display:flex; gap:14px; overflow-x:auto; padding:0 24px 24px; scroll-snap-type:x mandatory}
.strip figure{margin:0; flex:0 0 auto; scroll-snap-align:start}
.strip img{
  display:block; width:186px; border-radius:9px; border:1px solid var(--line);
  cursor:zoom-in; background:var(--ground);
}
.strip.story img{width:132px}
.strip figcaption{
  font-family:'IBM Plex Mono',monospace; font-size:10.5px; color:var(--ink-3);
  margin-top:7px; letter-spacing:.05em;
}

/* caption block */
.text-block{padding:0 24px 24px}
details{border-top:1px solid var(--line-soft)}
summary{
  padding:15px 24px; cursor:pointer; font-size:13px; font-weight:600;
  letter-spacing:.09em; text-transform:uppercase; color:var(--ink-2);
  list-style:none; display:flex; justify-content:space-between; align-items:center; gap:12px;
}
summary::-webkit-details-marker{display:none}
summary::after{content:'+'; font-family:'IBM Plex Mono',monospace; font-size:17px; color:var(--ink-3)}
details[open] summary::after{content:'−'}
summary:focus-visible{outline:2px solid var(--sage); outline-offset:-2px}
pre.cap{
  margin:0 24px 22px; padding:18px 20px; background:var(--ground);
  border:1px solid var(--line-soft); border-radius:10px;
  white-space:pre-wrap; font-family:inherit; font-size:14.5px; line-height:1.62;
  color:var(--ink-2); max-height:340px; overflow:auto;
}
.tags{
  margin:0 24px 22px; font-family:'IBM Plex Mono',monospace; font-size:12.5px;
  line-height:1.9; color:var(--sage); word-break:break-word;
}
.warn{
  margin:0 24px 22px; padding:14px 17px; border-radius:10px;
  background:var(--coral-soft); border:1px solid var(--coral); color:var(--ink);
  font-size:14px;
}
.warn b{color:var(--coral)}

/* checkbox */
.decide{
  display:flex; align-items:center; gap:11px; padding:16px 24px;
  border-top:1px solid var(--line-soft); font-size:14.5px; color:var(--ink-2);
}
.decide input{width:19px; height:19px; accent-color:var(--sage); cursor:pointer}
.decide label{cursor:pointer}

/* how-to */
.howto{border:1px solid var(--line); border-radius:14px; padding:28px 26px; background:var(--panel)}
.howto h3{font-family:'Fraunces',Georgia,serif; font-size:21px; font-weight:600; margin:0 0 18px}
.howto ol{margin:0; padding-left:0; list-style:none; counter-reset:s}
.howto li{
  counter-increment:s; position:relative; padding-left:44px; margin-bottom:15px;
  color:var(--ink-2); max-width:62ch;
}
.howto li::before{
  content:counter(s); position:absolute; left:0; top:1px;
  width:28px; height:28px; border-radius:8px; background:var(--sage-soft); color:var(--sage);
  font-family:'IBM Plex Mono',monospace; font-size:13px; font-weight:600;
  display:flex; align-items:center; justify-content:center;
}
.howto code{
  font-family:'IBM Plex Mono',monospace; font-size:13px;
  background:var(--ground); border:1px solid var(--line-soft);
  padding:2px 6px; border-radius:5px; color:var(--ink);
}
footer{margin-top:34px; color:var(--ink-3); font-size:13.5px}

/* lightbox */
#lb{
  position:fixed; inset:0; background:rgba(10,12,8,.9); display:none;
  align-items:center; justify-content:center; padding:26px; z-index:50; cursor:zoom-out;
}
#lb.on{display:flex}
#lb img{max-width:min(560px,92vw); max-height:92vh; border-radius:12px}
@media (prefers-reduced-motion:reduce){*{animation:none!important; transition:none!important}}
"""

JS = """
document.querySelectorAll('.strip img').forEach(function(i){
  i.addEventListener('click', function(){
    var lb=document.getElementById('lb');
    lb.querySelector('img').src=i.src; lb.classList.add('on');
  });
});
document.getElementById('lb').addEventListener('click',function(){this.classList.remove('on')});
document.addEventListener('keydown',function(e){
  if(e.key==='Escape') document.getElementById('lb').classList.remove('on');
});
document.querySelectorAll('.decide input').forEach(function(c){
  var k='pk-ok-'+c.dataset.id;
  try{ if(localStorage.getItem(k)==='1') c.checked=true; }catch(e){}
  c.addEventListener('change',function(){
    try{ localStorage.setItem(k, c.checked?'1':'0'); }catch(e){}
  });
});
"""


def card(item: dict) -> str:
    doc, kode = item["doc"], item["kode"]
    rows = item["rows"]
    status = rows[0]["status"]
    kat = TOK["kategori"].get(doc.get("kategori", "resep"), {"label": ""})["label"]

    jadwal = " · ".join(
        f"{r['tipe_konten'].replace('feed_carousel','Carousel').replace('feed_single','Single').replace('story','Story')}"
        f" {r['tanggal_posting']} {r['jam_posting']}" for r in rows)

    strip = "".join(
        f'<figure><img src="{src}" alt="Slide {i+1} {esc(kode)}" loading="lazy">'
        f'<figcaption>{i+1:02d}</figcaption></figure>'
        for i, src in enumerate(item["carousel"]))

    story = ""
    if item["story"]:
        hints = [s.get("sticker_hint") for s in doc.get("story", []) if s.get("sticker_hint")]
        warn = ""
        if hints:
            warn = ('<div class="warn"><b>Perlu tangan Anda.</b> API Instagram tidak bisa '
                    'memasang sticker interaktif. Story ini harus diposting manual lewat aplikasi:'
                    '<br>' + "<br>".join("· " + esc(h.replace("STICKER MANUAL: ", ""))
                                         for h in hints) + "</div>")
        story = (f'<div class="strip-head"><h3>Story</h3>'
                 f'<span class="hint">{len(item["story"])} frame</span></div>'
                 f'<div class="strip story">' + "".join(
                     f'<figure><img src="{src}" alt="Story {i+1}" loading="lazy">'
                     f'<figcaption>{i+1:02d}</figcaption></figure>'
                     for i, src in enumerate(item["story"])) + "</div>" + warn)

    foto_kurang = [im["id"] for im in doc.get("images", [])
                   if not (ROOT / "content" / f"{kode}_{doc['slug']}" / "img" / f"{im['id']}.png").exists()]
    fw = ""
    if foto_kurang:
        fw = (f'<div class="warn"><b>Foto belum dibuat.</b> Slide masih memakai kotak kosong '
              f'untuk: {esc(", ".join(foto_kurang))}. Jalankan workflow '
              f'<em>Render konten</em> dengan pilihan "buat foto AI" dicentang dulu.</div>')

    return f"""
<article class="card">
  <div class="card-top">
    <span class="kode">{esc(kode)}</span>
    <h2>{esc(doc.get('judul'))}</h2>
    <span class="pill {esc(status)}">{esc(status)}</span>
  </div>
  <dl class="meta">
    <div><dt>Kategori</dt><dd>{esc(kat)}</dd></div>
    <div><dt>Jadwal (WIB)</dt><dd>{esc(jadwal)}</dd></div>
    <div><dt>Slide</dt><dd>{len(item['carousel'])} carousel · {len(item['story'])} story</dd></div>
    <div><dt>Set hashtag</dt><dd>Set {esc(doc.get('hashtag_set','—'))}</dd></div>
  </dl>
  {fw}
  <div class="strip-head"><h3>Carousel</h3><span class="hint">ketuk untuk perbesar · geser →</span></div>
  <div class="strip">{strip}</div>
  {story}
  <details>
    <summary>Caption</summary>
    <pre class="cap">{esc(doc.get('caption'))}</pre>
  </details>
  <details>
    <summary>Hashtag — masuk ke komentar pertama, bukan caption</summary>
    <p class="tags">{esc(doc.get('hashtags'))}</p>
  </details>
  <div class="decide">
    <input type="checkbox" id="ok-{esc(kode)}" data-id="{esc(kode)}">
    <label for="ok-{esc(kode)}">Saya setuju konten ini tayang</label>
  </div>
</article>"""


def build(out: pathlib.Path):
    items = collect()
    n_slide = sum(len(i["carousel"]) + len(i["story"]) for i in items)
    n_wait = sum(1 for i in items if i["rows"][0]["status"] in ("draft", "review"))

    body = f"""
<div id="lb"><img src="" alt="Slide diperbesar"></div>
<div class="wrap">
<header>
  <p class="kicker">Antrean review · @piringkalori</p>
  <h1>Konten yang menunggu keputusan Anda</h1>
  <p class="lede">Semuanya sudah jadi file siap posting. Tidak ada satu pun yang akan
  tayang sebelum Anda mengubah statusnya menjadi <code>approved</code> di calendar.csv —
  centang di halaman ini hanya catatan untuk Anda sendiri.</p>
  <div class="tally">
    <b><span>{len(items)}</span> konten</b>
    <b><span>{n_wait}</span> menunggu persetujuan</b>
    <b><span>{n_slide}</span> gambar sudah dirender</b>
  </div>
</header>
{''.join(card(i) for i in items)}
<div class="howto">
  <h3>Cara menyetujui</h3>
  <ol>
    <li>Buka <code>calendar.csv</code> di repo GitHub, klik ikon pensil.</li>
    <li>Pada baris konten yang Anda setujui, ubah kolom <code>status</code>
        dari <code>draft</code> menjadi <code>approved</code>. Sekalian sesuaikan
        <code>tanggal_posting</code> dan <code>jam_posting</code> kalau perlu.</li>
    <li>Klik <code>Commit changes</code>. Robot akan mengeceknya dalam 15 menit
        dan menayangkannya tepat pada jam itu.</li>
  </ol>
  <p style="margin:20px 0 0; color:var(--ink-2); max-width:62ch">
    Mau membatalkan satu konten? Ubah statusnya jadi <code>skipped</code>.
    Mau menunda? Ganti tanggalnya saja — statusnya boleh tetap <code>approved</code>.
  </p>
</div>
<footer>Dirender otomatis dari content.json · palet, tipografi, dan tata letak mengikuti panduan brand Piringkalori.</footer>
</div>"""

    out.write_text(
        "<title>Antrean Konten Piringkalori</title>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Mono:wght@500;600&'
        'family=Public+Sans:wght@400;600&display=swap">\n'
        f"<style>{CSS}</style>\n{body}\n<script>{JS}</script>\n",
        encoding="utf-8")
    print(f"{out} — {len(items)} konten, {n_slide} gambar, "
          f"{out.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "preview.html"))
    build(pathlib.Path(ap.parse_args().out))
