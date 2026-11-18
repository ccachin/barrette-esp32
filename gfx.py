# gfx.py - couleurs, palette arc-en-ciel et rendu de texte agrandi.
import framebuf
import math


def rgb(r, g, b):
    """Couleur RGB565 deja 'byte-swappee' pour l'ecran (utiliser PARTOUT)."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


def wheel(p):
    p &= 255
    if p < 85:
        return rgb(255 - p * 3, p * 3, 0)
    if p < 170:
        p -= 85
        return rgb(0, 255 - p * 3, p * 3)
    p -= 170
    return rgb(p * 3, 0, 255 - p * 3)


PALETTE = [wheel(i) for i in range(256)]            # arc-en-ciel
SIN = [int(127 * math.sin(i * math.pi / 128)) for i in range(256)]

BLACK = 0
WHITE = rgb(255, 255, 255)
RED = rgb(255, 0, 0)
GREEN = rgb(0, 255, 0)
BLUE = rgb(0, 0, 255)
YELLOW = rgb(255, 220, 0)
ORANGE = rgb(255, 120, 0)
PINK = rgb(255, 80, 160)
CYAN = rgb(0, 220, 255)
PURPLE = rgb(160, 0, 255)

# La police integree ne connait que l'ASCII : on remplace les accents.
_MAP = {
    "é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "ä": "a",
    "î": "i", "ï": "i", "ô": "o", "ö": "o", "ù": "u", "û": "u", "ü": "u",
    "ç": "c", "É": "E", "È": "E", "Ê": "E", "À": "A", "Â": "A", "Î": "I",
    "Ô": "O", "Ù": "U", "Û": "U", "Ç": "C", "’": "'", "‘": "'", "“": '"',
    "”": '"', "–": "-", "—": "-", "…": "...", "€": "E", "œ": "oe", "Œ": "OE",
}


def fix_text(s):
    out = []
    for ch in s:
        if ord(ch) < 128:
            out.append(ch)
        else:
            out.append(_MAP.get(ch, "?"))
    return "".join(out)


def render_text(text, color=None, scale=6):
    """Dessine `text` agrandi `scale` fois dans un petit framebuffer RGB565.
    color=None -> une couleur arc-en-ciel par lettre. Fond noir = transparent au blit.
    Retourne (fb, buf, largeur, hauteur)."""
    text = fix_text(text) or " "
    n = len(text)
    w, h = n * 8 * scale, 8 * scale
    buf = bytearray(w * h * 2)
    fb = framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)
    cb = bytearray(8)
    cf = framebuf.FrameBuffer(cb, 8, 8, framebuf.MONO_HLSB)
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        cf.fill(0)
        cf.text(ch, 0, 0, 1)
        col = color if color is not None else PALETTE[(i * 256 // n) & 255]
        for y in range(8):
            row = cb[y]
            if not row:
                continue
            x = 0
            while x < 8:                      # regroupe les pixels voisins
                if row & (0x80 >> x):
                    x2 = x
                    while x2 < 8 and row & (0x80 >> x2):
                        x2 += 1
                    fb.fill_rect(i * 8 * scale + x * scale, y * scale,
                                 (x2 - x) * scale, scale, col)
                    x = x2
                else:
                    x += 1
    return fb, buf, w, h
