# qr.py - mini generateur de QR code pour MicroPython (mode octets, correction M, versions 1 a 6
# = jusqu'a 106 octets). Utilise par main.py pour afficher le QR de connexion Wi-Fi.
#   m = qr.encode("WIFI:T:WPA;S:Barrette;P:motdepasse;;")   -> liste de lignes (bytearray de 0/1)
#   qr.draw(d, m, x, y, box)                                  -> dessine sur l'ecran (fond blanc inclus)

# version : (octets de correction par bloc, nombre de blocs, octets de donnees par bloc)
_EC = {1: (10, 1, 16), 2: (16, 1, 28), 3: (26, 1, 44), 4: (18, 2, 32), 5: (24, 2, 43), 6: (16, 4, 27)}
_ALIGN = {1: 0, 2: 18, 3: 22, 4: 26, 5: 30, 6: 34}       # centre de l'unique motif d'alignement

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 256:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _rs(data, n):
    g = [1]
    for i in range(n):
        ng = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            ng[j] ^= c
            ng[j + 1] ^= _mul(c, _EXP[i])
        g = ng
    res = [0] * n
    for b in data:
        f = b ^ res[0]
        res = res[1:] + [0]
        if f:
            for i in range(n):
                res[i] ^= _mul(g[i + 1], f)
    return res


def _codewords(data, ver):
    ecn, nb, dl = _EC[ver]
    total = nb * dl
    bits = []

    def put(v, n):
        for i in range(n - 1, -1, -1):
            bits.append((v >> i) & 1)

    put(4, 4)
    put(len(data), 8)
    for b in data:
        put(b, 8)
    put(0, min(4, total * 8 - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    cw = [int("".join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(cw) < total:
        cw.append(pad)
        pad = 0x11 if pad == 0xEC else 0xEC
    blocks = [cw[i * dl:(i + 1) * dl] for i in range(nb)]
    eccs = [_rs(b, ecn) for b in blocks]
    out = []
    for i in range(dl):
        for b in blocks:
            out.append(b[i])
    for i in range(ecn):
        for e in eccs:
            out.append(e[i])
    return out


def _penalty(m, n):
    p = 0
    for rows in (m, [[m[r][c] for r in range(n)] for c in range(n)]):
        for row in rows:
            run, last = 1, row[0]
            for v in row[1:]:
                if v == last:
                    run += 1
                else:
                    if run >= 5:
                        p += run - 2
                    run, last = 1, v
            if run >= 5:
                p += run - 2
            s = "".join("1" if v else "0" for v in row)
            p += 40 * (s.count("10111010000") + s.count("00001011101"))
    for r in range(n - 1):
        a, b = m[r], m[r + 1]
        for c in range(n - 1):
            if a[c] == a[c + 1] == b[c] == b[c + 1]:
                p += 3
    dark = sum(sum(r) for r in m)
    p += 10 * (abs(dark * 100 // (n * n) - 50) // 5)
    return p


_MASKS = (
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
)


def _fmt_bits(mask):                       # correction M = 00
    rem = mask << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return ((mask << 10) | rem) ^ 0x5412


def encode(text, mask=None):
    data = text.encode() if isinstance(text, str) else bytes(text)
    ver = 0
    for v in (1, 2, 3, 4, 5, 6):
        if len(data) <= _EC[v][1] * _EC[v][2] - 2:
            ver = v
            break
    if not ver:
        raise ValueError("texte trop long pour le QR (max 106 octets)")
    n = 17 + 4 * ver
    m = [bytearray(n) for _ in range(n)]
    res = [bytearray(n) for _ in range(n)]

    def setm(r, c, v):
        m[r][c] = 1 if v else 0
        res[r][c] = 1

    for fr, fc in ((0, 0), (0, n - 7), (n - 7, 0)):                 # reperes + separateurs
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = fr + dr, fc + dc
                if 0 <= r < n and 0 <= c < n:
                    setm(r, c, 0 <= dr <= 6 and 0 <= dc <= 6 and
                         (dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4)))
    for i in range(8, n - 8):                                       # synchronisation
        setm(6, i, i % 2 == 0)
        setm(i, 6, i % 2 == 0)
    if ver > 1:                                                     # alignement
        a = _ALIGN[ver]
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                setm(a + dr, a + dc, max(abs(dr), abs(dc)) != 1)
    setm(n - 8, 8, 1)                                               # module sombre
    for i in range(9):                                              # zones de format
        res[8][i] = res[i][8] = 1
    for i in range(8):
        res[8][n - 1 - i] = res[n - 1 - i][8] = 1

    cw = _codewords(data, ver)
    bits = []
    for b in cw:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    bits += [0] * 7 if ver > 1 else []
    idx, col, up = 0, n - 1, True
    while col > 0:
        if col == 6:
            col -= 1
        for r in (range(n - 1, -1, -1) if up else range(n)):
            for c in (col, col - 1):
                if not res[r][c]:
                    m[r][c] = bits[idx] if idx < len(bits) else 0
                    idx += 1
        up = not up
        col -= 2

    def build(k):
        t = [bytearray(row) for row in m]
        f = _MASKS[k]
        for r in range(n):
            for c in range(n):
                if not res[r][c] and f(r, c):
                    t[r][c] ^= 1
        fb = _fmt_bits(k)
        for i in range(15):
            v = (fb >> i) & 1
            if i < 6:
                t[i][8] = v
            elif i < 8:
                t[i + 1][8] = v
            else:
                t[n - 15 + i][8] = v
            if i < 8:
                t[8][n - i - 1] = v
            elif i < 9:
                t[8][7] = v
            else:
                t[8][15 - i - 1] = v
        t[n - 8][8] = 1
        return t

    if mask is not None:
        return build(mask)
    best, bp = None, 1 << 30
    for k in range(8):
        t = build(k)
        p = _penalty(t, n)
        if p < bp:
            best, bp = t, p
    return best


def draw(d, m, x, y, box, bg=0xFFFF, fg=0):
    """Dessine le QR (avec 2 modules de marge blanche) a la position x, y de l'ecran d."""
    n = len(m)
    q = 2
    d.fill_rect(x, y, (n + 2 * q) * box, (n + 2 * q) * box, bg)
    for r in range(n):
        row = m[r]
        c = 0
        while c < n:
            if row[c]:
                c2 = c
                while c2 < n and row[c2]:
                    c2 += 1
                d.fill_rect(x + (q + c) * box, y + (q + r) * box, (c2 - c) * box, box, fg)
                c = c2
            else:
                c += 1
    return (n + 2 * q) * box
