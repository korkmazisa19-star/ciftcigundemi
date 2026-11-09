#!/usr/bin/env python3
"""Instagram Reels kapağı: uret.py'nin kart.jpg'sini 1080x1920 tuvale yerleştirir.
Kart, ızgaranın kırptığı 3:4 alanın (y 240-1680) içinde kalır; kalan alan kartın bulanık hali.

Kullanım: python3 _build/sosyal/kapak.py <kart.jpg> <kapak.jpg>
"""
import sys
from PIL import Image, ImageEnhance, ImageFilter

W, H = 1080, 1920


def main(kart, cikti):
    k = Image.open(kart).convert("RGB")
    k = k.resize((W, round(k.height * W / k.width)), Image.LANCZOS)
    o = max(W / k.width, H / k.height)
    z = k.resize((round(k.width * o) + 1, round(k.height * o) + 1), Image.LANCZOS)
    x, y = (z.width - W) // 2, (z.height - H) // 2
    z = z.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(40))
    z = ImageEnhance.Brightness(z).enhance(0.45)
    z.paste(k, (0, (H - k.height) // 2))
    z.save(cikti, quality=90, optimize=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
