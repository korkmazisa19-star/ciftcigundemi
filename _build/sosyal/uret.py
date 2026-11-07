#!/usr/bin/env python3
"""Sosyal medya kartı (1080x1350 JPG) ve 10 sn'lik dikey video (1080x1920 MP4) üretir.

Kullanım:
  python3 _build/sosyal/uret.py <haber-id> [--alt "kart alt satırı"] [--cikti /tmp/sosyal]
  MUZIK_ANAHTARI ortam değişkeni verilirse şifreli müzik çözülüp videoya eklenir.

Depo kökünden çalıştırılır (data/haberler.json ve assets/ okunur).
"""
import argparse, html, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
BURASI = Path(__file__).resolve().parent
SARI = "#f7c948"


def fontlari_kur():
    hedef = Path.home() / ".fonts"
    hedef.mkdir(exist_ok=True)
    yeni = False
    for f in (BURASI / "fonts").glob("*.otf"):
        if not (hedef / f.name).exists():
            shutil.copy(f, hedef / f.name)
            yeni = True
    if yeni:
        subprocess.run(["fc-cache", "-f"], check=False, capture_output=True)


def chrome_yolu():
    for ad in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        p = shutil.which(ad)
        if p:
            return p
    sys.exit("Chrome bulunamadı")


def gorsel_bul(veri, h):
    if h.get("gorsel"):
        return KOK / h["gorsel"], h.get("gorselKaynak") or "Temsili fotoğraf"
    f = veri.get("fotograflar", {})
    havuz = f.get("havuz", {}).get(h.get("motif") or "", [])
    if havuz:
        # sitedekiyle aynı mantık olmasa da id'ye göre sabit bir seçim yapar
        i = sum(ord(c) for c in h["id"]) % len(havuz)
        return KOK / f.get("klasor", "assets/foto/") / havuz[i], "Temsili fotoğraf"
    return None, "Temsili fotoğraf"


def manset_html(m):
    m = html.escape(m.replace("i", "İ").replace("ı", "I").upper())
    # "..." veya “...” arasını sarı-kalın yap
    m = re.sub(r'(&quot;|“)(.+?)(&quot;|”)', lambda x: f'<b>“{x.group(2)}”</b>', m)
    return m


def kart_html(h, foto, kaynak, renk, alt):
    kat = html.escape((h.get("kategori") or "").replace("i", "İ").replace("ı", "I").upper())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0}}*{{box-sizing:border-box}}
.k{{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:Inter,sans-serif;background:#111 url('{foto.as_uri() if foto else ''}') center 30%/cover}}
.k:before{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.55) 0%,rgba(0,0,0,0) 18%,rgba(0,0,0,0) 34%,rgba(8,14,9,.82) 58%,rgba(8,14,9,.96) 100%)}}
.logo{{position:absolute;left:64px;top:56px;height:62px}}
.not{{position:absolute;right:56px;top:66px;color:rgba(255,255,255,.8);font-size:22px;font-weight:500}}
.alt{{position:absolute;left:64px;right:64px;bottom:96px}}
.kat{{display:inline-block;background:{renk};color:#fff;font-weight:800;font-size:28px;letter-spacing:.08em;padding:10px 20px;border-radius:6px}}
h1{{margin:30px 0 0;color:#fff;font-weight:900;font-size:{92 if len(h.get('manset',''))<=30 else 80}px;line-height:1.02;letter-spacing:-.01em;text-shadow:0 4px 18px rgba(0,0,0,.6)}}
h1 b{{color:{SARI};font-weight:900}}
p{{margin:30px 0 0;color:#e8eee6;font-size:38px;line-height:1.3;font-weight:500;max-width:900px}}
.c{{margin-top:44px;display:flex;align-items:center;gap:18px;color:#fff;font-size:30px;font-weight:700}}
.c span{{background:{SARI};color:#1c321e;padding:10px 20px;border-radius:6px;font-weight:800}}
</style></head><body><div class="k"><img class="logo" src="{(BURASI/'logok.svg').as_uri()}"><div class="not">{html.escape(kaynak)}</div>
<div class="alt"><span class="kat">{kat}</span><h1>{manset_html(h.get('manset') or h['baslik'])}</h1><p>{html.escape(alt)}</p>
<div class="c"><span>ciftcigundemi.com</span> Haberin tamamı sitede</div></div></div></body></html>"""


def varsayilan_alt(h):
    s = re.split(r"(?<=[.!?])\s", (h.get("ozet") or "").strip())[0]
    return s if len(s) <= 120 else s[:117].rsplit(" ", 1)[0] + "…"


def zemin(kart, hedef):
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
    F = BURASI / "fonts"
    f_top = ImageFont.truetype(str(F / "Inter-Black.otf"), 64)
    f_sm = ImageFont.truetype(str(F / "Inter-Bold.otf"), 40)
    im = Image.open(kart).convert("RGB")
    b = im.resize((1536, 1920)).crop((228, 0, 1308, 1920)).filter(ImageFilter.GaussianBlur(40))
    b = ImageEnhance.Brightness(b).enhance(0.45)
    d = ImageDraw.Draw(b)
    t1, t2 = "ÇİFTÇİ ", "GÜNDEMİ"
    w1, w2 = d.textlength(t1, font=f_top), d.textlength(t2, font=f_top)
    x = (1080 - w1 - w2) / 2
    d.text((x, 150), t1, font=f_top, fill="white")
    d.text((x + w1, 150), t2, font=f_top, fill=SARI)
    s = "Tarım haberleri her gün"
    d.text(((1080 - d.textlength(s, font=f_sm)) / 2, 235), s, font=f_sm, fill=(220, 220, 220))
    s2 = "Takip et, tarım gündemini kaçırma!"
    w = d.textlength(s2, font=f_sm)
    d.rounded_rectangle(((1080 - w) / 2 - 30, 1640, (1080 + w) / 2 + 30, 1720), radius=40, fill=SARI)
    d.text(((1080 - w) / 2, 1655), s2, font=f_sm, fill=(20, 20, 20))
    b.save(hedef)


def muzik_coz(gecici):
    anahtar = os.environ.get("MUZIK_ANAHTARI")
    sifreli = BURASI / "muzik.mp3.enc"
    if not anahtar or not sifreli.exists():
        return None
    cikti = Path(gecici) / "muzik.mp3"
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(sifreli),
                        "-out", str(cikti), "-pass", "env:MUZIK_ANAHTARI"], capture_output=True)
    return cikti if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--alt")
    ap.add_argument("--cikti", default="/tmp/sosyal")
    a = ap.parse_args()

    veri = json.loads((KOK / "data/haberler.json").read_text())
    h = next((x for x in veri["haberler"] if x["id"] == a.id), None)
    if not h:
        sys.exit(f"Haber yok: {a.id}")
    renkler = {k["ad"]: k.get("renk", "#2f7d32") for k in veri.get("kategoriler", [])}
    foto, kaynak = gorsel_bul(veri, h)
    alt = a.alt or varsayilan_alt(h)

    out = Path(a.cikti) / a.id
    out.mkdir(parents=True, exist_ok=True)
    fontlari_kur()
    with tempfile.TemporaryDirectory() as g:
        sayfa = Path(g) / "kart.html"
        sayfa.write_text(kart_html(h, foto, kaynak, renkler.get(h.get("kategori"), "#2f7d32"), alt))
        png = Path(g) / "kart.png"
        subprocess.run([chrome_yolu(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--force-device-scale-factor=1",
                        "--window-size=1080,1350", f"--screenshot={png}", sayfa.as_uri()],
                       check=True, capture_output=True, timeout=120)
        from PIL import Image
        Image.open(png).convert("RGB").save(out / "kart.jpg", quality=90)
        zemin(out / "kart.jpg", Path(g) / "zemin.png")

        muz = muzik_coz(g)
        filtre = ("[1:v]scale=w='trunc(1080*(0.90+0.006*t)/2)*2':h=-2:eval=frame[c];"
                  "[0:v][c]overlay=x='(W-w)/2':y='(H-h)/2+20':format=auto,format=yuv420p[v]")
        k = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", "10", "-i", f"{g}/zemin.png",
             "-loop", "1", "-framerate", "30", "-t", "10", "-i", str(out / "kart.jpg")]
        if muz:
            k += ["-i", str(muz), "-filter_complex",
                  filtre + ";[2:a]atrim=0:10,afade=t=in:d=0.3,afade=t=out:st=8.8:d=1.2,loudnorm=I=-14:TP=-1.5[a]",
                  "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        else:
            k += ["-filter_complex", filtre, "-map", "[v]"]
        k += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-t", "10", "-movflags", "+faststart", str(out / "video.mp4")]
        subprocess.run(k, check=True)
    print(json.dumps({"kart": str(out / "kart.jpg"), "video": str(out / "video.mp4"), "muzik": bool(muz)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
