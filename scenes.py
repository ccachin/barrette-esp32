# scenes.py - les animations. Chaque "scene" est un objet avec :
#   start(d, S)        appelee au debut
#   frame(d, S, t)     dessine une image (t = ms depuis le debut) ; retourne True pour finir
# d = ecran, S = reglages (S["message"], S["brightness"]...)
import os
import random
import gc
from gfx import *


class Scene:
    title = "Scene"
    direct = False          # True si la scene envoie elle-meme l'image a l'ecran

    def __init__(self, duration=None):
        self.duration = duration        # secondes ; None = jusqu'a la fin naturelle

    def start(self, d, S):
        pass

    def frame(self, d, S, t):
        return True


class Scroll(Scene):
    """Message defilant de droite a gauche. text=None -> utilise le message reglable (web)."""
    title = "Texte defilant"

    def __init__(self, text=None, color=None, scale=6, speed=140, bg=0, duration=None):
        super().__init__(duration)
        self.text, self.color, self.scale, self.speed, self.bg = text, color, scale, speed, bg

    def start(self, d, S):
        self.fb = None
        gc.collect()
        self.fb, self.buf, self.tw, self.th = render_text(
            self.text or S["message"], self.color, self.scale)
        self.y = (d.height - self.th) // 2

    def frame(self, d, S, t):
        x = d.width - (t * self.speed) // 1000
        d.fill(self.bg)
        d.blit(self.fb, x, self.y, 0)
        return x + self.tw < 0


class Text(Scene):
    """Texte fixe centre avec un cadre arc-en-ciel anime. text=None -> message reglable."""
    title = "Texte fixe"

    def __init__(self, text=None, color=None, scale=None, border=True, bg=0, duration=6):
        super().__init__(duration)
        self.text, self.color, self.scale, self.border, self.bg = text, color, scale, border, bg

    def start(self, d, S):
        txt = self.text or S["message"]
        n = max(1, len(fix_text(txt)))
        sc = min(self.scale or 99, (d.width - 24) // (8 * n), (d.height - 24) // 8)
        self.fb, self.buf, self.tw, self.th = render_text(txt, self.color, max(1, sc))

    def frame(self, d, S, t):
        d.fill(self.bg)
        d.blit(self.fb, (d.width - self.tw) // 2, (d.height - self.th) // 2, 0)
        if self.border:
            for i in range(4):
                d.rect(i, i, d.width - 2 * i, d.height - 2 * i, PALETTE[(t // 5 + i * 16) & 255])
        return False


class Rainbow(Scene):
    title = "Arc-en-ciel"

    def __init__(self, speed=80, duration=8):
        super().__init__(duration)
        self.speed = speed

    def frame(self, d, S, t):
        o = t * self.speed // 1000
        h = d.height
        for x in range(0, d.width, 4):
            d.fill_rect(x, 0, 4, h, PALETTE[(x // 2 + o) & 255])
        return False


class Plasma(Scene):
    title = "Plasma"

    def __init__(self, block=10, duration=8):
        super().__init__(duration)
        self.block = block

    def frame(self, d, S, t):
        b = self.block
        a, c, e, g = t // 12, t // 17, t // 9, t // 20
        cols = [SIN[(bx * 2 + a) & 255] for bx in range(0, d.width, b)]
        for by in range(0, d.height, b):
            sy = SIN[(by * 3 + c) & 255]
            for i, bx in enumerate(range(0, d.width, b)):
                v = cols[i] + sy + SIN[(bx + by + e) & 255]
                d.fill_rect(bx, by, b, b, PALETTE[(v // 3 + g) & 255])
        return False


_GREENS = [rgb(0, 255 - i * 15, 0) for i in range(16)]
_CH = "0123456789ABCDEFGHJKLMNPRSTUVXYZ#$%&@*+=<>"


class Matrix(Scene):
    title = "Pluie numerique"

    def __init__(self, duration=8):
        super().__init__(duration)

    def start(self, d, S):
        self.cols = d.width // 8
        self.rows = d.height // 8 + 1
        n = self.cols
        self.pos = [random.randrange(-self.rows, 0) for _ in range(n)]
        self.spd = [random.randrange(8, 24) for _ in range(n)]
        self.trl = [random.randrange(6, 16) for _ in range(n)]
        self.chars = [[random.choice(_CH) for _ in range(self.rows)] for _ in range(n)]
        self.last = 0

    def frame(self, d, S, t):
        dt = t - self.last
        self.last = t
        d.fill(0)
        for c in range(self.cols):
            self.pos[c] += self.spd[c] * dt / 1000
            head = int(self.pos[c])
            if head - self.trl[c] > self.rows:
                self.pos[c] = random.randrange(-8, 0)
                self.spd[c] = random.randrange(8, 24)
                self.trl[c] = random.randrange(6, 16)
                continue
            tl = self.trl[c]
            for k in range(tl):
                row = head - k
                if 0 <= row < self.rows:
                    if k == 0:
                        col = WHITE
                        self.chars[c][row] = random.choice(_CH)
                    else:
                        col = _GREENS[k * 15 // tl]
                    d.text(self.chars[c][row], c * 8, row * 8, col)
        return False


_GRAY = [rgb(i, i, min(255, i + 30)) for i in range(256)]


class Stars(Scene):
    title = "Voyage dans les etoiles"

    def __init__(self, count=90, speed=110, duration=8):
        super().__init__(duration)
        self.count, self.speed = count, speed

    def _new(self, far=False):
        return [random.randrange(-200, 200), random.randrange(-120, 120),
                random.randrange(20, 256) if far else 255.0]

    def start(self, d, S):
        self.stars = [self._new(True) for _ in range(self.count)]
        self.last = 0

    def frame(self, d, S, t):
        dt = t - self.last
        self.last = t
        d.fill(0)
        cx, cy = d.width // 2, d.height // 2
        for i, s in enumerate(self.stars):
            s[2] -= self.speed * dt / 1000
            if s[2] < 3:
                self.stars[i] = s = self._new()
            z = s[2]
            sx = int(s[0] * 128 / z) + cx
            sy = int(s[1] * 128 / z) + cy
            if not (0 <= sx < d.width and 0 <= sy < d.height):
                self.stars[i] = self._new()
                continue
            br = 255 - int(z)
            size = 1 + br // 90
            d.fill_rect(sx, sy, size, size, _GRAY[br])
        return False


_HEART = ("0110110", "1111111", "1111111", "0111110", "0011100", "0001000")
_SPANS = []
for _y, _row in enumerate(_HEART):
    _x = 0
    while _x < 7:
        if _row[_x] == "1":
            _x2 = _x
            while _x2 < 7 and _row[_x2] == "1":
                _x2 += 1
            _SPANS.append((_y, _x, _x2 - _x))
            _x = _x2
        else:
            _x += 1
_PINKS = [rgb(255, 40, 90), rgb(255, 105, 180), rgb(255, 0, 60),
          rgb(255, 150, 200), rgb(220, 0, 110)]


class Hearts(Scene):
    title = "Coeurs"

    def __init__(self, count=12, bg=rgb(20, 0, 12), duration=8):
        super().__init__(duration)
        self.count, self.bg = count, bg

    def _new(self, d, anywhere=False):
        return [random.randrange(0, d.width), random.randrange(0, d.height) if anywhere else d.height + 10,
                random.randrange(25, 70), random.randrange(2, 6), random.choice(_PINKS),
                random.randrange(0, 256)]

    def start(self, d, S):
        self.h = [self._new(d, True) for _ in range(self.count)]
        self.last = 0

    def frame(self, d, S, t):
        dt = t - self.last
        self.last = t
        d.fill(self.bg)
        for i, h in enumerate(self.h):
            h[1] -= h[2] * dt / 1000
            sc = h[3]
            if h[1] < -7 * sc:
                self.h[i] = h = self._new(d)
                sc = h[3]
            x = h[0] + SIN[(h[5] + t // 8) & 255] // 8
            y = int(h[1])
            for (ry, rx, rw) in _SPANS:
                d.fill_rect(x + rx * sc, y + ry * sc, rw * sc, sc, h[4])
        return False


class Anim(Scene):
    """Joue des images .raw d'un dossier (voir tools/gif2raw.py)."""
    title = "Animation (images)"
    direct = True

    def __init__(self, folder, fps=12, loops=3, duration=None):
        super().__init__(duration)
        self.folder, self.fps, self.loops = folder, fps, loops

    def start(self, d, S):
        size = d.width * d.height * 2
        try:
            names = sorted(n for n in os.listdir(self.folder) if n.endswith(".raw"))
        except OSError:
            names = []
        self.paths = [self.folder + "/" + n for n in names
                      if os.stat(self.folder + "/" + n)[6] == size]
        self.frames = None
        gc.collect()
        if self.paths and len(self.paths) * size <= 3_000_000:      # tout en RAM = fluide
            self.frames = []
            for p in self.paths:
                with open(p, "rb") as f:
                    self.frames.append(f.read())

    def frame(self, d, S, t):
        n = len(self.paths)
        if not n:
            d.fill(0)
            d.text("Aucune image", 10, 10, WHITE)
            d.text(self.folder, 10, 24, WHITE)
            d.show()
            return True
        i = t * self.fps // 1000
        if i >= n * self.loops:
            return True
        i %= n
        if self.frames:
            d.show_raw(self.frames[i])
        else:
            with open(self.paths[i], "rb") as f:
                f.readinto(d.buf)
            d.show_raw(d.buf)
        return False
