#!/usr/bin/env python3
"""Sosyal medya için 1080x1920 dikey haber videosu (kanca başlık, altyazı, seslendirme, müzik).

Kullanım (depo kökünden):
  python3 _build/sosyal/dikey.py <haber-id> --ust "Erzincan'da buzağı desteği" --sari "Son gün 1 Aralık" \
      --ses ses.mp3 --metin "Seslendirilen metin" --muzik muzik.mp3 --cikti /tmp/sosyal [--x 0.5]

Haberde `video` alanı varsa o görüntü arka plan olur (kendi sesi kullanılmaz); yoksa `gorsel` yakınlaşarak gösterilir.
--x: yatay kadraj merkezi (0-1). Çıktı: <cikti>/<id>/video.mp4
"""
import argparse, json, re, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parents[2]
FONT = Path(__file__).resolve().parent / "fonts"
W, H, FPS = 1080, 1920, 30
SARI, BEYAZ, KOYU = (247, 201, 72), (255, 255, 255), (18, 24, 16)


def TR(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def font(ad, boy):
    return ImageFont.truetype(str(FONT / ad), boy)


def sigdir(d, metin, ad, boy, genislik):
    while boy > 30 and d.textlength(metin, font=font(ad, boy)) > genislik:
        boy -= 2
    return font(ad, boy)


def sure(yol):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yol)]))


def konusma_araliklari(ses, uzunluk):
    cikti = subprocess.run(["ffmpeg", "-nostats", "-i", str(ses), "-af", "silencedetect=n=-35dB:d=0.12", "-f", "null", "-"], capture_output=True, text=True).stderr
    basla = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", cikti)]
    bitis = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", cikti)]
    ar, t = [], 0.0
    for a, b in zip(basla, bitis):
        if a > t + 0.05:
            ar.append((t, a))
        t = b
    if uzunluk > t + 0.05:
        ar.append((t, uzunluk))
    return ar


def kelime_zamanlari(metin, ar, gecikme):
    kelimeler = metin.split()
    toplam_harf = sum(len(k) + 1 for k in kelimeler)
    toplam_sure = sum(b - a for a, b in ar)

    def zaman(oran):
        kalan = oran * toplam_sure
        for a, b in ar:
            if kalan <= b - a:
                return a + kalan
            kalan -= b - a
        return ar[-1][1]

    sonuc, harf = [], 0
    for k in kelimeler:
        bas = zaman(harf / toplam_harf)
        harf += len(k) + 1
        sonuc.append((bas + gecikme, zaman(harf / toplam_harf) + gecikme, TR(k)))
    return sonuc


def gruplar(z):
    g, i = [], 0
    while i < len(z):
        k = 2 if i + 1 < len(z) and len(z[i][2]) + len(z[i + 1][2]) > 15 else 3
        g.append(z[i:i + k])
        i += k
    return g


def maske():
    m = Image.new("L", (1, H), 0)
    for y in range(H):
        v = int(150 * (1 - y / 520)) if y < 520 else (int(225 * min(1, (y - 1050) / 500)) if y > 1050 else 0)
        m.putpixel((0, y), v)
    return m.resize((W, H))


def ortala(d, y, metin, f, renk):
    d.text(((W - d.textlength(metin, font=f)) / 2, y), metin, font=f, fill=renk)


def ciz(zemin, t, sure_toplam, ust, sari, kaynak, grp, m, siyah):
    im = Image.composite(siyah, zemin, m)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((60, 70, 1020, 175), radius=18, fill=BEYAZ)
    ortala(d, 92, ust, sigdir(d, ust, "Inter-Black.otf", 58, 900), KOYU)
    d.rounded_rectangle((60, 185, 1020, 300), radius=18, fill=SARI)
    ortala(d, 200, sari, sigdir(d, sari, "Inter-Black.otf", 80, 900), KOYU)
    d.text((40, 1845), kaynak, font=font("Inter-Medium.otf", 30), fill=(230, 230, 230))
    f = font("Inter-ExtraBold.otf", 34)
    d.text((W - 40 - d.textlength("ÇİFTÇİ GÜNDEMİ", font=f), 1842), "ÇİFTÇİ GÜNDEMİ", font=f, fill=BEYAZ)
    if t >= sure_toplam - 1.0:
        d.rounded_rectangle((110, 1420, 970, 1600), radius=24, fill=SARI)
        ortala(d, 1445, "Tarım gündemini kaçırma", font("Inter-Black.otf", 58), KOYU)
        ortala(d, 1525, "Takip et: Çiftçi Gündemi", font("Inter-Bold.otf", 46), KOYU)
        return im
    aktif = None
    for i, g in enumerate(grp):
        son = grp[i + 1][0][0] if i + 1 < len(grp) else sure_toplam - 1.0
        if g[0][0] <= t < son:
            aktif = g
            break
    if aktif:
        fn = font("Inter-Black.otf", 84)
        tum = " ".join(x[2] for x in aktif)
        satirlar = [aktif] if d.textlength(tum, font=fn) < 980 else [aktif[:-1], aktif[-1:]]
        y = 1460 if len(satirlar) == 1 else 1400
        for sat in satirlar:
            x = (W - d.textlength(" ".join(k[2] for k in sat), font=fn)) / 2
            for bas, bit, k in sat:
                d.text((x, y), k, font=fn, fill=SARI if bas <= t < bit else BEYAZ, stroke_width=6, stroke_fill=(0, 0, 0))
                x += d.textlength(k + " ", font=fn)
            y += 110
    return im


def main():
    a = argparse.ArgumentParser()
    a.add_argument("id")
    for ad in ("--ust", "--sari", "--ses", "--metin", "--muzik", "--cikti"):
        a.add_argument(ad, required=True)
    a.add_argument("--x", type=float, default=0.5)
    o = a.parse_args()
    veri = json.load(open(KOK / "data/haberler.json", encoding="utf-8"))
    h = next(x for x in veri["haberler"] if x["id"] == o.id)
    gecikme = 0.3
    uz = sure(o.ses)
    toplam = min(15.0, max(10.0, round(uz + gecikme + 1.3, 2)))
    grp = gruplar(kelime_zamanlari(o.metin, konusma_araliklari(o.ses, uz), gecikme))
    kaynak = re.sub(r"\s*\(temsili\)", "", h.get("gorselKaynak") or "")
    m, siyah = maske(), Image.new("RGB", (W, H), (0, 0, 0))
    hedef = Path(o.cikti) / o.id
    hedef.mkdir(parents=True, exist_ok=True)
    gecici = Path(tempfile.mkdtemp())
    try:
        kare_sayi = int(toplam * FPS)
        video = KOK / h["video"] if h.get("video") else None
        if video:
            (gecici / "z").mkdir()
            subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-t", str(toplam), "-vf",
                                   f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})*{o.x}:0,fps={FPS}", "-q:v", "3", str(gecici / "z/%05d.jpg")])
            zeminler = sorted((gecici / "z").glob("*.jpg"))
            if not zeminler:
                raise SystemExit("video okunamadı")
        else:
            ph = Image.open(KOK / h["gorsel"]).convert("RGB")
            gen = int(ph.height * W / H)
            x0 = max(0, min(ph.width - gen, int(ph.width * o.x) - gen // 2))
            taban = ph.crop((x0, 0, x0 + gen, ph.height)).resize((int(W * 1.18), int(H * 1.18)), Image.LANCZOS)
        (gecici / "k").mkdir()
        for n in range(kare_sayi):
            t = n / FPS
            if video:
                zemin = Image.open(zeminler[min(n, len(zeminler) - 1)]).convert("RGB")
            else:
                z = 1 + 0.16 * t / toplam
                cw, ch = int(W * 1.18 / z), int(H * 1.18 / z)
                bx = (taban.width - cw) // 2
                zemin = taban.crop((bx, 0, bx + cw, ch)).resize((W, H), Image.BILINEAR)
            ciz(zemin, t, toplam, o.ust, o.sari, kaynak, grp, m, siyah).save(gecici / f"k/{n:05d}.jpg", quality=90)
        ses_son = round(gecikme + uz, 2)
        filtre = (f"[1:a]adelay={int(gecikme*1000)}|{int(gecikme*1000)},aresample=48000,aformat=channel_layouts=stereo[v];"
                  f"[2:a]atrim=0:{toplam},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                  f"volume='if(lt(t,{ses_son}),0.126,min(1,0.126+(t-{ses_son})/0.4*0.874))':eval=frame,afade=t=out:st={toplam-0.7}:d=0.7[m];"
                  f"[v][m]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,atrim=0:{toplam}[a]")
        subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(gecici / "k/%05d.jpg"), "-i", o.ses, "-i", o.muzik,
                               "-filter_complex", filtre, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-t", str(toplam), "-movflags", "+faststart", str(hedef / "video.mp4")])
        print(json.dumps({"video": str(hedef / "video.mp4"), "sure": toplam}, ensure_ascii=False))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    main()
