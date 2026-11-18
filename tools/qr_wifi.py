# qr_wifi.py - A lancer sur le PC (pip install qrcode pillow).
# Cree un QR code qui fait rejoindre le Wi-Fi de la barrette en le scannant avec l'appareil photo.
# Usage : python qr_wifi.py [chemin/vers/config.py]   (lit AP_SSID et AP_PASSWORD dans config.py puis config_local.py, le dernier gagne)
# Produit :
#   qr_wifi_imprimer.png   : a imprimer (autocollant, carte...)
#   qr_wifi_barrette.png   : 320x172, a envoyer sur la barrette via la page web (section Images)
import re
import sys
import qrcode
from PIL import Image, ImageDraw, ImageFont

import os

# lit config.py puis config_local.py (reglages personnels, prioritaires) ; ou un chemin donne en argument
files = [sys.argv[1]] if len(sys.argv) > 1 else ["../config.py", "../config_local.py"]
txt = "".join(open(f, encoding="utf-8").read() + "\n" for f in files if os.path.exists(f))


def get(key):
    found = re.findall(r'^%s\s*=\s*"([^"]*)"' % key, txt, re.M)
    return found[-1]                       # la derniere valeur gagne (config_local apres config)


ssid, pwd = get("AP_SSID"), get("AP_PASSWORD")


def esc(s):
    for ch in '\\;,:"':
        s = s.replace(ch, "\\" + ch)
    return s


payload = "WIFI:T:WPA;S:%s;P:%s;;" % (esc(ssid), esc(pwd))
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2, box_size=1)
qr.add_data(payload)
qr.make(fit=True)
n = qr.modules_count + 4                      # modules + marge (quiet zone)
font = ImageFont.load_default()

# 1) version barrette 320x172 : QR a gauche (carre), infos a droite
box = 172 // n
img = Image.new("RGB", (320, 172), "white")
m = qr.make_image(fill_color="black", back_color="white").convert("RGB")
m = m.resize((n * box, n * box), Image.NEAREST)
img.paste(m, (0, (172 - n * box) // 2))
d = ImageDraw.Draw(img)
x = n * box + 10
for i, line in enumerate(("Scanne pour", "te connecter :", "", ssid, "", "mdp :", pwd)):
    d.text((x, 20 + i * 16), line, fill="black", font=font)
img.save("qr_wifi_barrette.png")

# 2) version a imprimer
big = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((n * 16, n * 16), Image.NEAREST)
page = Image.new("RGB", (big.width, big.height + 40), "white")
page.paste(big, (0, 0))
ImageDraw.Draw(page).text((10, big.height + 12), "Wi-Fi : %s   mdp : %s" % (ssid, pwd), fill="black", font=font)
page.save("qr_wifi_imprimer.png")
print("QR crees pour :", payload)
