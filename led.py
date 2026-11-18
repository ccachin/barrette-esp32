# led.py - pilote de la LED WS2812 sous l'ecran (GPIO38) + effets lumineux.
# Chaque scene a un effet par defaut (DEFAULT_LED). Pour en choisir un autre dans la PLAYLIST de config.py :
#   leds(Synthwave(duration=12), "pulse", (255, 0, 200), 2400)
# Format d'un effet : (nom, couleur (r,g,b) ou None = couleur qui change, parametre)
#   ("off",)                         eteinte
#   ("solid", (r,g,b))               fixe
#   ("rainbow",)                     arc-en-ciel
#   ("pulse", (r,g,b), periode_ms)   respiration
#   ("beat", (r,g,b), bpm)           battement (flash puis decroit)
#   ("chase", (r,g,b), periode_ms)   comete qui tourne (utile si plusieurs LED)
#   ("twinkle",)                     scintillement multicolore
#   ("glitch",)                      clignotements cyan / magenta
import neopixel
from machine import Pin


def _wheel(p):
    p &= 255
    if p < 85:
        return (255 - p * 3, p * 3, 0)
    if p < 170:
        p -= 85
        return (0, 255 - p * 3, p * 3)
    p -= 170
    return (p * 3, 0, 255 - p * 3)


DEFAULT_LED = {
    "Scroll": ("rainbow",),
    "Text": ("pulse", None, 2000),
    "Rainbow": ("rainbow",),
    "Plasma": ("rainbow",),
    "Matrix": ("chase", (0, 255, 70), 900),
    "Stars": ("twinkle",),
    "Hearts": ("pulse", (255, 40, 110), 900),
    "Anim": ("rainbow",),
    "Equalizer": ("beat", None, 128),
    "Synthwave": ("pulse", (255, 0, 200), 2400),
    "Rings": ("beat", (0, 200, 255), 158),
    "Sparkles": ("twinkle",),
    "Waves": ("pulse", (255, 90, 160), 3000),
    "Fireworks": ("twinkle",),
    "Spiro": ("rainbow",),
    "Glitch": ("glitch",),
    "Dancefloor": ("beat", None, 120),
}

# Choix possibles depuis la page web (cle, libelle). "auto" = effet de la scene.
LED_CHOICES = (
    ("auto", "Auto (selon la scene)"),
    ("rainbow", "Arc-en-ciel"),
    ("pink", "Respiration rose"),
    ("cyan", "Respiration cyan"),
    ("beat", "Battement disco"),
    ("white", "Blanc fixe"),
    ("off", "Eteinte"),
)
OVERRIDES = {
    "rainbow": ("rainbow",),
    "pink": ("pulse", (255, 40, 150), 2000),
    "cyan": ("pulse", (0, 220, 255), 2000),
    "beat": ("beat", None, 128),
    "white": ("solid", (255, 255, 255)),
    "off": ("off",),
}


def leds(scene, *mode):
    """Associe un effet LED a une scene et la renvoie : leds(Hearts(duration=8), "beat", (255, 0, 100), 140)"""
    scene.led = mode
    return scene


def led_mode(scene, choice):
    if choice in OVERRIDES:
        return OVERRIDES[choice]
    custom = getattr(scene, "led", None)
    if custom:
        return custom
    name = type(scene).__name__
    if name == "Neon":
        return ("pulse", scene.color, 2200)
    return DEFAULT_LED.get(name, ("rainbow",))


class Led:
    def __init__(self, pin=38, n=1, brightness=30, order="RGB"):
        self.n = n
        self.np = neopixel.NeoPixel(Pin(pin, Pin.OUT), n)
        self.idx = [("RGB").index(c) for c in order]
        self.k = 0
        self.set_brightness(brightness)

    def set_brightness(self, pct):
        self.k = max(0, min(100, int(pct))) * 256 // 100

    def _put(self, i, c, lvl=255):
        k = self.k * lvl >> 8
        v = (c[0] * k >> 8, c[1] * k >> 8, c[2] * k >> 8)
        self.np[i] = (v[self.idx[0]], v[self.idx[1]], v[self.idx[2]])

    def update(self, t, mode):
        name = mode[0]
        col = mode[1] if len(mode) > 1 else None
        par = mode[2] if len(mode) > 2 else None
        n = self.n
        put = self._put
        if name == "off":
            for i in range(n):
                self.np[i] = (0, 0, 0)
        elif name == "solid":
            c = col or _wheel(t // 20)
            for i in range(n):
                put(i, c)
        elif name == "rainbow":
            for i in range(n):
                put(i, _wheel(t // 8 + i * 256 // n))
        elif name == "pulse":
            per = par or 2000
            ph = (t % per) * 512 // per
            lvl = ph if ph < 256 else 511 - ph
            lvl = lvl * lvl >> 8
            c = col or _wheel(t // 30)
            for i in range(n):
                put(i, c, lvl)
        elif name == "beat":
            per = 60000 // (par or 120)
            lvl = 255 - (t % per) * 255 // per
            lvl = lvl * lvl >> 8
            c = col or _wheel((t // per) * 40)
            for i in range(n):
                put(i, c, lvl)
        elif name == "chase":
            per = par or 900
            pos = (t % per) * n / per
            c = col or _wheel(t // 20)
            for i in range(n):
                dd = (pos - i) % n
                put(i, c, max(0, 255 - int(dd * 255 / max(1.0, n / 2))))
        elif name == "twinkle":
            for i in range(n):
                per = 700 + i * 130
                u = t + i * 331
                ph = (u % per) * 512 // per
                lvl = ph if ph < 256 else 511 - ph
                put(i, _wheel(t // 40 + i * 70 + (u // per) * 53), lvl * lvl >> 8)
        elif name == "glitch":
            h = ((t // 90) * 2654435761) & 0xFFFF
            if h % 7 == 0:
                c, lvl = (0, 0, 0), 0
            elif h % 3 == 0:
                c, lvl = (255, 0, 200), 255
            else:
                c, lvl = (0, 220, 255), 255
            for i in range(n):
                put(i, c, lvl)
        self.np.write()
