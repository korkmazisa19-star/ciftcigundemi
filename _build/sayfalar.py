#!/usr/bin/env python3
"""Çiftçi Gündemi: her haber için statik sayfa, site haritası, RSS ve 404 sayfası üretir.
index.html ve data/haberler.json'dan çalışır. Kök dizinden çalıştırın: python3 _build/sayfalar.py"""
import json, os, re, html, shutil, datetime
from email.utils import format_datetime

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://ciftcigundemi.com"
TZ = datetime.timezone(datetime.timedelta(hours=3))

def e(s): return html.escape(str(s if s is not None else ""), quote=True)

def i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x

def tohum(s):
    h = i32(2166136261)
    for ch in s:
        h = i32(h ^ ord(ch))
        h = i32((h * 16777619) & 0xFFFFFFFF)
    st = [h]
    def r():
        h = st[0]
        h = i32(h ^ i32(h << 13))
        h = i32(h ^ ((h & 0xFFFFFFFF) >> 17))
        h = i32(h ^ i32(h << 5))
        st[0] = h
        return ((h & 0xFFFFFFFF) % 10000) / 10000
    return r

def foto_ata(V):
    fh = V.get("fotograflar") or {}
    havuz = fh.get("havuz") or {}
    FOTO, kul = {}, {}
    sirali = sorted(V["haberler"], key=lambda h: (h["tarih"], [-ord(c) for c in h["id"]]), reverse=True)
    # JS: tarih azalan, eşitlikte id artan
    sirali = sorted(V["haberler"], key=lambda h: h["id"])
    sirali = sorted(sirali, key=lambda h: h["tarih"], reverse=True)
    for h in sirali:
        if h.get("gorsel"): continue
        l = havuz.get(h.get("motif")) or []
        if not l: continue
        u = kul.setdefault(h["motif"], {})
        if len(u) >= len(l):
            u = kul[h["motif"]] = {}
        r = tohum(h["id"]); i = int(r() * len(l))
        k = 0
        while k < len(l) and u.get(i):
            i = (i + 1) % len(l); k += 1
        u[i] = 1; FOTO[h["id"]] = l[i]
    return FOTO

def gorsel_yol(h, V, FOTO):
    if h.get("gorsel"): return h["gorsel"]
    if h["id"] in FOTO: return (V["fotograflar"].get("klasor") or "assets/foto/") + FOTO[h["id"]]
    return "assets/logo-profil-1080.png"

def zaman(h):
    z = h.get("eklenme")
    if z: return z
    return h["tarih"] + "T09:00:00+03:00"

AY = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
def tr_tarih(iso):
    y, m, d = iso[:10].split("-"); return f"{int(d)} {AY[int(m)-1]} {y}"

def paragraflar(ozet):
    p = re.split(r"(?<=\.)\s+(?=[A-ZÇĞİÖŞÜ0-9])", ozet)
    y = (len(p) + 1) // 2
    out = [" ".join(p[:y])]
    if len(p) > 1: out.append(" ".join(p[y:]))
    return out

def sayfa(tpl, h, V, FOTO):
    url = f"{SITE}/haber/{h['id']}/"
    img = SITE + "/" + gorsel_yol(h, V, FOTO).lstrip("/")
    acik = h["ozet"]
    acik = (acik[:157].rsplit(" ", 1)[0] + "…") if len(acik) > 160 else acik
    baslik = f"{h['baslik']} · Çiftçi Gündemi"
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": h["baslik"][:110],
          "description": acik, "image": [img], "datePublished": zaman(h), "dateModified": zaman(h),
          "articleSection": h.get("kategori"), "inLanguage": "tr-TR", "mainEntityOfPage": url,
          "author": {"@type": "Organization", "name": "Çiftçi Gündemi", "url": SITE + "/"},
          "publisher": {"@type": "Organization", "name": "Çiftçi Gündemi",
                        "logo": {"@type": "ImageObject", "url": SITE + "/assets/logo-profil-1080.png"}}}
    bas = (f'<title>{e(baslik)}</title>\n<meta name="description" content="{e(acik)}">\n'
           f'<link rel="canonical" href="{url}">\n'
           f'<meta property="og:title" content="{e(h["baslik"])}">\n<meta property="og:description" content="{e(acik)}">\n'
           f'<meta property="og:type" content="article">\n<meta property="og:url" content="{url}">\n'
           f'<meta property="og:image" content="{e(img)}">\n<meta property="og:site_name" content="Çiftçi Gündemi">\n'
           f'<meta property="og:locale" content="tr_TR">\n<meta property="article:published_time" content="{zaman(h)}">\n'
           f'<meta property="article:section" content="{e(h.get("kategori"))}">\n'
           f'<meta name="twitter:card" content="summary_large_image">\n'
           f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    out = tpl
    out = re.sub(r"<title>.*?</title>", lambda m: "", out, count=1, flags=re.S)
    for pat in [r'<meta name="description"[^>]*>\n?', r'<meta property="og:[a-z_:]+"[^>]*>\n?', r'<link rel="canonical"[^>]*>\n?']:
        out = re.sub(pat, "", out)
    out = out.replace('<base href="/">', '<base href="/">\n' + bas, 1)
    govde = (f'<article><nav class="yol"><a href="/">Ana sayfa</a></nav><header class="haber-bas"><h1>{e(h["baslik"])}</h1>'
             f'<div class="meta"><span class="kat">{e(h.get("kategori"))}</span><span>{tr_tarih(h["tarih"])}</span></div></header>'
             f'<div class="haber-govde"><div class="gorsel"><img src="/{e(gorsel_yol(h, V, FOTO))}" alt="{e(h["baslik"])}"></div>'
             f'<div class="haber-metin">' + "".join(f"<p>{e(p)}</p>" for p in paragraflar(h["ozet"])) + "</div>"
             + (f'<div class="ne-yapmali"><strong>Ne yapmalı?</strong><p>{e(h["neYapmali"])}</p></div>' if h.get("neYapmali") else "")
             + '<div class="kaynak-satir"><span>Kaynak:</span>' + "".join(f'<a href="{e(k["url"])}" rel="noopener">{e(k["ad"])}</a>' for k in h.get("kaynaklar", [])) + "</div></div></article>")
    out = re.sub(r'(<main class="kap" id="icerik">)(.*?)(</main>)', lambda m: m.group(1) + govde + m.group(3), out, count=1, flags=re.S)
    return out

def main():
    tpl = open(os.path.join(KOK, "index.html"), encoding="utf-8").read()
    V = json.load(open(os.path.join(KOK, "data", "haberler.json"), encoding="utf-8"))
    FOTO = foto_ata(V)
    hd = os.path.join(KOK, "haber")
    if os.path.isdir(hd): shutil.rmtree(hd)
    haberler = sorted(V["haberler"], key=zaman, reverse=True)
    for h in haberler:
        if not re.fullmatch(r"[a-z0-9-]{3,120}", h["id"]): continue
        d = os.path.join(hd, h["id"]); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(sayfa(tpl, h, V, FOTO))
    # 404
    t404 = tpl.replace('<base href="/">', '<base href="/">\n<meta name="robots" content="noindex">', 1)
    open(os.path.join(KOK, "404.html"), "w", encoding="utf-8").write(t404)
    # sitemap (+ Google News: son 2 gün)
    simdi = datetime.datetime.now(TZ)
    sat = [f'<url><loc>{SITE}/</loc><lastmod>{simdi.isoformat(timespec="seconds")}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>']
    for h in haberler:
        z = zaman(h); ek = ""
        try:
            if simdi - datetime.datetime.fromisoformat(z) < datetime.timedelta(days=2):
                ek = (f'<news:news><news:publication><news:name>Çiftçi Gündemi</news:name><news:language>tr</news:language></news:publication>'
                      f'<news:publication_date>{z}</news:publication_date><news:title>{e(h["baslik"])}</news:title></news:news>')
        except ValueError: pass
        sat.append(f'<url><loc>{SITE}/haber/{h["id"]}/</loc><lastmod>{z}</lastmod>{ek}</url>')
    open(os.path.join(KOK, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "\n".join(sat) + "\n</urlset>\n")
    # RSS
    ogeler = []
    for h in haberler[:40]:
        url = f"{SITE}/haber/{h['id']}/"
        try: pd = format_datetime(datetime.datetime.fromisoformat(zaman(h)))
        except ValueError: pd = ""
        ogeler.append(f"<item><title>{e(h['baslik'])}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                      f"<category>{e(h.get('kategori'))}</category><pubDate>{pd}</pubDate><description>{e(h['ozet'])}</description>"
                      f"<enclosure url=\"{e(SITE + '/' + gorsel_yol(h, V, FOTO))}\" type=\"image/jpeg\" length=\"0\"/></item>")
    open(os.path.join(KOK, "rss.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>Çiftçi Gündemi</title><link>{SITE}/</link><description>Destek, hibe, son başvuru tarihleri, tarım fiyatları ve zirai don uyarıları.</description>'
        f'<language>tr</language><atom:link href="{SITE}/rss.xml" rel="self" type="application/rss+xml"/>'
        f'<lastBuildDate>{format_datetime(simdi)}</lastBuildDate>' + "".join(ogeler) + "</channel></rss>\n")
    print(f"{len(haberler)} haber sayfası, sitemap, rss ve 404 üretildi")

if __name__ == "__main__":
    main()
