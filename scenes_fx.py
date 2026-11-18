# scenes_fx.py - animations "electro / rétro-futuriste / girly" en plus de scenes.py.
# Chaque scene s'utilise dans la PLAYLIST de config.py, ex. : Synthwave(duration=12)
import math
import os
import random
from scenes import Scene
from gfx import *


def _mix(c, k):
    """c = (r, g, b), k = 0..256 (luminosite) -> couleur ecran."""
    return rgb(c[0] * k >> 8, c[1] * k >> 8, c[2] * k >> 8)


def _lerp(a, b, t):
    """melange de deux (r, g, b), t = 0..255."""
    return tuple(a[i] + (b[i] - a[i]) * t // 255 for i in range(3))


def _wheel_t(p):
    p &= 255
    if p < 85:
        return (255 - p * 3, p * 3, 0)
    if p < 170:
        p -= 85
        return (0, 255 - p * 3, p * 3)
    p -= 170
    return (p * 3, 0, 255 - p * 3)


_PT = [_wheel_t(i) for i in range(256)]


def _fit(d, txt, margin):
    n = max(1, len(fix_text(txt)))
    return max(1, min((d.width - margin) // (8 * n), (d.height - margin) // 8, 12))


# ---------------------------------------------------------------------------
class Equalizer(Scene):
    """Egaliseur electro qui bat en rythme (BPM reglable)."""
    title = "Equaliseur"
    SEGS = 14

    def __init__(self, bars=20, bpm=128, duration=12):
        super().__init__(duration)
        self.n, self.beat_ms = bars, 60000 // bpm

    def start(self, d, S):
        n = self.n
        self.lv, self.pk, self.tg = [0.0] * n, [0.0] * n, [0.0] * n
        self.last = self.tt = 0
        self.grad = [rgb(*_lerp((0, 230, 255), (255, 0, 200), i * 255 // (self.SEGS - 1)))
                     for i in range(self.SEGS)]

    def frame(self, d, S, t):
        dt = (t - self.last) / 1000
        self.last = t
        n, W, H, SEGS = self.n, d.width, d.height, self.SEGS
        kick = 1 - (t % self.beat_ms) / self.beat_ms
        if t - self.tt > 90:
            self.tt = t
            for i in range(n):
                self.tg[i] = 0.12 + 0.55 * kick * (1 - 0.6 * i / n) + random.random() * 0.3
        d.fill(rgb(6, 0, 14))
        bw = W // n
        x0 = (W - n * bw) // 2
        segh = (H - 8) // SEGS
        for i in range(n):
            lv = self.lv[i]
            tg = self.tg[i]
            if tg > lv:
                lv += (tg - lv) * min(1.0, 16 * dt)
            else:
                lv -= 1.4 * dt
            lv = 0.0 if lv < 0 else (1.0 if lv > 1 else lv)
            self.lv[i] = lv
            pk = self.pk[i]
            pk = lv if lv > pk else max(0.0, pk - 0.35 * dt)
            self.pk[i] = pk
            x = x0 + i * bw + 1
            nseg = int(lv * SEGS)
            for s in range(nseg):
                d.fill_rect(x, H - 4 - (s + 1) * segh, bw - 3, segh - 2, self.grad[s])
            ps = int(pk * SEGS)
            if ps > nseg:
                d.fill_rect(x, H - 4 - ps * segh, bw - 3, segh - 2, WHITE)
        return False


# ---------------------------------------------------------------------------
class Synthwave(Scene):
    """Soleil retro, horizon et grille en perspective (style annees 80)."""
    title = "Synthwave"

    def __init__(self, speed=1.0, duration=12):
        super().__init__(duration)
        self.speed = speed

    def start(self, d, S):
        W, H = d.width, d.height
        self.hz = H * 58 // 100
        self.sky = [rgb(*_lerp((8, 0, 40), (255, 50, 130), y * 255 // self.hz))
                    for y in range(0, self.hz, 4)]
        self.stars = [(random.randrange(W), random.randrange(self.hz * 2 // 3)) for _ in range(25)]
        r = 46
        self.r = r
        self.sun = []
        for dy in range(-r, r, 2):
            hw = int(math.sqrt(r * r - dy * dy))
            self.sun.append((dy, hw, rgb(*_lerp((255, 230, 60), (255, 30, 140), (dy + r) * 255 // (2 * r)))))

    def frame(self, d, S, t):
        W, H, hz, r = d.width, d.height, self.hz, self.r
        cx, cy = W // 2, hz - 8
        for i, c in enumerate(self.sky):
            d.fill_rect(0, i * 4, W, 4, c)
        for i, (x, y) in enumerate(self.stars):
            if (t // 250 + i) % 4:
                d.pixel(x, y, WHITE)
        for dy, hw, c in self.sun:
            d.fill_rect(cx - hw, cy + dy, 2 * hw, 2, c)
        off = (t // 110) % 9
        for k in range(6):
            sy = cy + 2 + k * 9 + off
            th = 2 + k // 2
            if sy < hz:
                d.fill_rect(cx - r, sy, 2 * r, th, self.sky[min(len(self.sky) - 1, sy // 4)])
        d.fill_rect(0, hz, W, H - hz, rgb(18, 0, 36))
        mag = rgb(230, 0, 220)
        d.hline(0, hz, W, rgb(255, 120, 255))
        n = 8
        f = (t * self.speed / 1000) % 1.0
        for i in range(n):
            u = (i + f) / n
            y = hz + int(u * u * (H - hz))
            if y < H:
                d.hline(0, y, W, mag)
        for j in range(-9, 10):
            d.line(cx + j * 4, hz, cx + j * 48, H - 1, mag)
        return False


# ---------------------------------------------------------------------------
class Rings(Scene):
    """Ondes neon qui partent du centre, comme un sonar / une pulsation."""
    title = "Ondes neon"

    def __init__(self, speed=110, gap=380, duration=10):
        super().__init__(duration)
        self.speed, self.gap = speed, gap

    def frame(self, d, S, t):
        d.fill(rgb(4, 0, 10))
        cx, cy = d.width // 2, d.height // 2
        top = t // self.gap
        for k in range(max(0, top - 9), top + 1):
            r = (t - k * self.gap) * self.speed // 1000
            if r < 2 or r > 260:
                continue
            col = PALETTE[(k * 28 + t // 25) & 255]
            d.ellipse(cx, cy, r, r, col)
            d.ellipse(cx, cy, r + 1, r + 1, col)
        d.ellipse(cx, cy, 6, 6, WHITE, True)
        return False


# ---------------------------------------------------------------------------
class Sparkles(Scene):
    """Paillettes qui scintillent (rose, or, cyan, lilas)."""
    title = "Paillettes"
    COLS = ((255, 80, 170), (255, 210, 90), (90, 230, 255), (255, 255, 255), (190, 120, 255))

    def __init__(self, count=30, bg=(8, 0, 18), duration=10):
        super().__init__(duration)
        self.count, self.bg = count, rgb(*bg)

    def _new(self, d, t):
        return [random.randrange(8, d.width - 8), random.randrange(8, d.height - 8),
                t, random.randrange(600, 1800), random.choice(self.COLS)]

    def start(self, d, S):
        self.sp = [self._new(d, -random.randrange(0, 1500)) for _ in range(self.count)]

    def frame(self, d, S, t):
        d.fill(self.bg)
        for i, s in enumerate(self.sp):
            age = t - s[2]
            if age < 0:
                continue
            if age > s[3]:
                self.sp[i] = self._new(d, t)
                continue
            ph = age * 256 // s[3]
            b = ph * 2 if ph < 128 else (256 - ph) * 2
            sz = 1 + b * 6 // 256
            col = _mix(s[4], b)
            x, y = s[0], s[1]
            d.fill_rect(x - sz, y, 2 * sz + 2, 2, col)
            d.fill_rect(x, y - sz, 2, 2 * sz + 2, col)
            if b > 200:
                d.fill_rect(x - 1, y - 1, 4, 4, WHITE)
        return False


# ---------------------------------------------------------------------------
class Waves(Scene):
    """Vagues pastel superposees (coucher de soleil / aurore)."""
    title = "Vagues pastel"

    def __init__(self, duration=12):
        super().__init__(duration)
        # (couleur, ligne de base, amplitude, frequence, lenteur)
        self.layers = ((rgb(70, 0, 140), 60, 30, 3, 9), (rgb(0, 150, 170), 90, 28, 4, 7),
                       (rgb(255, 70, 160), 120, 22, 5, 6), (rgb(255, 170, 90), 148, 14, 6, 5))

    def frame(self, d, S, t):
        H = d.height
        d.fill(rgb(10, 0, 30))
        for col, base, amp, k, sp in self.layers:
            for x in range(0, d.width, 4):
                y = base + SIN[(x * k // 2 + t // sp) & 255] * amp // 127
                d.fill_rect(x, y, 4, H - y, col)
        return False


# ---------------------------------------------------------------------------
class Fireworks(Scene):
    """Feux d'artifice."""
    title = "Feux d'artifice"
    COLS = ((255, 80, 170), (255, 210, 90), (90, 230, 255), (190, 120, 255), (120, 255, 150))

    def __init__(self, duration=12):
        super().__init__(duration)

    def start(self, d, S):
        self.rk, self.sp = [], []
        self.last = 0
        self.next = 0

    def frame(self, d, S, t):
        dt = (t - self.last) / 1000
        self.last = t
        W, H = d.width, d.height
        d.fill(rgb(2, 0, 8))
        if t >= self.next:
            self.next = t + random.randrange(500, 1100)
            self.rk.append([random.randrange(40, W - 40), float(H), random.randrange(25, 90),
                            random.choice(self.COLS)])
        alive = []
        for r in self.rk:
            r[1] -= 170 * dt
            if r[1] <= r[2]:
                for k in range(36):
                    a = 6.2832 * k / 36 + random.random() * 0.3
                    v = random.randrange(40, 110)
                    self.sp.append([r[0], r[1], math.cos(a) * v, math.sin(a) * v,
                                    0, random.randrange(700, 1300), r[3]])
            else:
                d.fill_rect(int(r[0]), int(r[1]), 2, 5, WHITE)
                alive.append(r)
        self.rk = alive
        alive = []
        for s in self.sp[-220:]:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 80 * dt
            s[4] += dt * 1000
            if s[4] < s[5]:
                d.fill_rect(int(s[0]), int(s[1]), 2, 2, _mix(s[6], 256 - int(s[4] * 256 / s[5])))
                alive.append(s)
        self.sp = alive
        return False


# ---------------------------------------------------------------------------
class Spiro(Scene):
    """Courbes de Lissajous / spirographe arc-en-ciel."""
    title = "Spirographe"
    RAT = ((3, 2), (5, 4), (4, 3), (5, 6))

    def __init__(self, duration=16):
        super().__init__(duration)

    def frame(self, d, S, t):
        d.fill(rgb(3, 0, 10))
        cx, cy = d.width // 2, d.height // 2
        ax, ay = cx - 6, cy - 6
        fx, fy = self.RAT[(t // 4000) % len(self.RAT)]
        p, q = t / 1500, t / 2300
        N = 140
        px = py = 0
        for i in range(N + 1):
            a = i * 6.2832 / N
            x = cx + int(ax * math.sin(fx * a + p))
            y = cy + int(ay * math.sin(fy * a + q))
            if i:
                d.line(px, py, x, y, PALETTE[(i * 3 + t // 12) & 255])
            px, py = x, y
        return False


# ---------------------------------------------------------------------------
class Glitch(Scene):
    """Texte 'glitch' cyberpunk (decalage cyan / magenta). text=None -> message reglable."""
    title = "Texte glitch"

    def __init__(self, text=None, duration=8):
        super().__init__(duration)
        self.text = text

    def start(self, d, S):
        txt = self.text or S["message"]
        sc = _fit(d, txt, 40)
        self.w = render_text(txt, WHITE, sc)
        self.c = render_text(txt, CYAN, sc)
        self.m = render_text(txt, rgb(255, 0, 200), sc)
        self.nextg = 400
        self.gend = 0

    def frame(self, d, S, t):
        W, H = d.width, d.height
        d.fill(rgb(4, 0, 10))
        line = rgb(14, 0, 26)
        for y in range(0, H, 4):
            d.hline(0, y, W, line)
        if t >= self.nextg:
            self.nextg = t + random.randrange(600, 1800)
            self.gend = t + random.randrange(80, 220)
        g = t < self.gend
        o = random.randrange(4, 14) if g else 2
        jx = random.randrange(-10, 10) if g else 0
        tw, th = self.w[2], self.w[3]
        x, y = (W - tw) // 2 + jx, (H - th) // 2
        d.blit(self.c[0], x - o, y, 0)
        d.blit(self.m[0], x + o, y, 0)
        d.blit(self.w[0], x, y, 0)
        if g:
            for _ in range(4):
                d.fill_rect(0, random.randrange(H), W, random.randrange(2, 7),
                            random.choice((CYAN, rgb(255, 0, 200), BLACK)))
        return False


# ---------------------------------------------------------------------------
class Neon(Scene):
    """Enseigne neon qui grésille. text=None -> message reglable ; color = (r, g, b)."""
    title = "Neon"

    def __init__(self, text=None, color=(255, 40, 170), duration=8):
        super().__init__(duration)
        self.text, self.color = text, color

    def start(self, d, S):
        txt = self.text or S["message"]
        sc = _fit(d, txt, 56)
        c = self.color
        self.glow = render_text(txt, _mix(c, 70), sc)
        self.mid = render_text(txt, _mix(c, 170), sc)
        self.core = render_text(txt, rgb(min(255, c[0] + 110), min(255, c[1] + 110), min(255, c[2] + 110)), sc)
        self.fl = 0

    def frame(self, d, S, t):
        W, H = d.width, d.height
        d.fill(rgb(3, 0, 8))
        if random.random() < 0.015:
            self.fl = t + random.randrange(60, 200)
        on = t >= self.fl
        col = rgb(*self.color) if on else _mix(self.color, 60)
        d.rect(6, 6, W - 12, H - 12, col)
        d.rect(7, 7, W - 14, H - 14, col)
        tw, th = self.core[2], self.core[3]
        x, y = (W - tw) // 2, (H - th) // 2
        if on:
            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, -3), (-3, 3), (3, 3)):
                d.blit(self.glow[0], x + dx, y + dy, 0)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                d.blit(self.mid[0], x + dx, y + dy, 0)
        d.blit(self.core[0], x, y, 0)
        return False


# ---------------------------------------------------------------------------
class Dancefloor(Scene):
    """Piste de danse disco : dalles colorees qui pulsent en rythme."""
    title = "Dancefloor"

    def __init__(self, cell=20, bpm=120, duration=12):
        super().__init__(duration)
        self.cell, self.bpm = cell, bpm

    def frame(self, d, S, t):
        cs = self.cell
        beat = t * self.bpm // 60000
        ph = (t * self.bpm % 60000) / 60000
        bright = 256 - int(ph * 150)
        dark = rgb(10, 0, 20)
        d.fill(rgb(2, 0, 6))
        for j, cy in enumerate(range(0, d.height, cs)):
            for i, cx in enumerate(range(0, d.width, cs)):
                if (i + j + beat) & 1:
                    col = _mix(_PT[(i * 12 + j * 12 + beat * 25 + t // 30) & 255], bright)
                else:
                    col = dark
                d.fill_rect(cx + 1, cy + 1, cs - 2, cs - 2, col)
        return False


# ---------------------------------------------------------------------------
class Gallery(Scene):
    """Diaporama des images envoyees depuis la page web (dossier images/).
    Si une image est choisie sur la page web ("Afficher"), elle reste affichee."""
    title = "Images (galerie)"
    direct = True

    def __init__(self, folder="images", seconds=6):
        super().__init__(None)
        self.folder, self.seconds = folder, seconds

    def start(self, d, S):
        size = d.width * d.height * 2
        try:
            names = sorted(n for n in os.listdir(self.folder) if n.endswith(".raw"))
        except OSError:
            names = []
        only = S.get("image") or ""
        self.single = bool(only) and (only + ".raw") in names
        if self.single:
            names = [only + ".raw"]
        self.paths = []
        for n in names:
            p = self.folder + "/" + n
            if os.stat(p)[6] == size:
                self.paths.append(p)
        self.shown = -1

    def frame(self, d, S, t):
        n = len(self.paths)
        if not n:
            d.fill(0)
            d.text("Aucune image", 10, 10, WHITE)
            d.text("Ajoute-en depuis la page web", 10, 26, WHITE)
            d.show()
            return t > 2500
        if self.single:
            i = 0
        else:
            i = t // (self.seconds * 1000)
            if i >= n:
                return True
        if i != self.shown:
            self.shown = i
            with open(self.paths[i], "rb") as f:
                f.readinto(d.buf)
            d.show_raw(d.buf)
        return False
