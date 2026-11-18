# gif2raw.py - A lancer sur le PC (pip install pillow).
# Usage : python gif2raw.py mon.gif frames/mon_anim [largeur=320] [hauteur=172] [max_images=60]
# Copier ensuite le dossier frames/mon_anim sur la carte et ajouter dans config.py :
#   Anim("frames/mon_anim", fps=12)
import os
import sys
from PIL import Image, ImageOps, ImageSequence

src, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 320
h = int(sys.argv[4]) if len(sys.argv) > 4 else 172
maxn = int(sys.argv[5]) if len(sys.argv) > 5 else 60
os.makedirs(out, exist_ok=True)

for n, fr in enumerate(ImageSequence.Iterator(Image.open(src))):
    if n >= maxn:
        break
    im = ImageOps.pad(fr.convert("RGB"), (w, h), color=(0, 0, 0))
    data = bytearray(w * h * 2)
    for i, (r, g, b) in enumerate(im.getdata()):
        c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data[2 * i] = c >> 8                      # big-endian, comme l'ecran
        data[2 * i + 1] = c & 255
    with open("%s/f%03d.raw" % (out, n), "wb") as f:
        f.write(data)
print("%d images ecrites dans %s (%d Ko chacune)" % (n + 1 if n < maxn else maxn, out, w * h * 2 // 1024))
