"""LFPAK33 junction-to-air thermal resistance against copper (pcb-blocks poe_pd, Ion-Speakers#15).

Vendor data: Nexperia AN90003 Rev 5.0 (12 Feb 2026), LFPAK MOSFET thermal design guide. LFPAK33 on FR4 1.6 mm,
100 x 100 mm board, still air at 20 C (p19, p25). The tab-net copper is an x by x mm square, the same on every
layer, stitched with vias (Table 7 p26). Curves digitized from the rendered pages by curve colour (+-2 C):
  Fig. 25 p20: one top layer, 2 oz (70 um).                0.5 W and 1 W curves
  Fig. 35 p27: four layers + vias, 2 oz on every layer.     0.5 W and 1 W curves
  Fig. 41 p31: two LFPAK33 2 mm apart on one 2 oz layer, 0.5 W each (the neighbour's extra rise)
Rth(j-a) = (Tj - 20) / P, applied at the block's 50 C air.

Judgement (Jeff, Ion-Speakers#15 item 4): copper on stitched layers counts as one sheet of the summed thickness.
70 um = Fig. 25; 280 um = Fig. 35; between them Rth is interpolated in ln(thickness). Each layer's copper is
counted once: the square is the copper on one layer (the smallest), never the sum of the layers' areas.
Below 70 um only (F.Cu alone), a radial-fin model fitted to Fig. 25 scales the curve: general knowledge
(conduction plus a fitted surface coefficient), flagged where it's used.

The same model and curves as wallnode-amp calc/poe_pd_fet_copper_layers.py (Ion-Speakers, d9db9d5).
"""
import math

F25_05 = {5: 179.0, 6: 151.5, 7: 131.4, 8: 118.0, 9: 107.0, 10: 98.5, 11: 91.3, 12: 85.6, 13: 80.9, 14: 76.5, 15: 73.0,
          16: 70.1, 18: 64.5, 20: 60.1, 22: 56.5, 25: 53.3, 28: 50.4, 30: 49.0, 35: 45.8, 40: 43.9, 45: 42.5, 50: 41.3}
F25_1 = {9: 179.7, 10: 165.2, 11: 152.2, 12: 142.2, 13: 133.2, 14: 125.3, 15: 118.9, 16: 113.5, 18: 104.6, 20: 97.4,
         22: 91.3, 25: 84.7, 28: 79.5, 30: 76.7, 35: 71.8, 40: 66.6, 45: 65.7, 50: 63.6}
F35_05 = {4: 166.8, 5: 144.5, 6: 122.9, 7: 108.9, 8: 99.7, 9: 90.1, 10: 83.5, 11: 78.8, 12: 74.6, 13: 70.4, 14: 66.6,
          15: 63.3, 16: 60.5, 18: 56.1, 20: 52.3, 22: 49.3, 25: 45.5, 28: 42.5, 30: 40.6, 35: 36.4, 40: 35.0, 45: 33.1,
          50: 31.7}
F35_1 = {8: 175.2, 9: 153.4, 10: 137.9, 11: 128.8, 12: 120.8, 13: 113.8, 14: 107.4, 15: 101.3, 16: 96.4, 18: 88.7,
         20: 82.1, 22: 76.2, 25: 69.2, 28: 64.0, 30: 61.2, 35: 54.7, 40: 50.0, 45: 46.7, 50: 43.9}
F41_ONE = {6: 150.4, 7: 131.1, 8: 117.7, 9: 106.8, 10: 98.4, 11: 91.5, 12: 85.9, 13: 81.0, 14: 76.7, 15: 73.4, 16: 70.4,
           18: 65.0, 20: 60.5, 22: 57.2, 25: 53.7, 28: 50.8, 30: 49.2, 35: 46.1, 40: 44.0, 45: 42.6}
F41_TWO = {6: 167.8, 7: 145.2, 8: 129.4, 9: 116.7, 10: 106.8, 11: 98.8, 12: 92.3, 13: 86.6, 14: 81.0, 15: 77.0, 16: 73.4,
           18: 67.8, 20: 63.3, 22: 59.5, 25: 55.5, 28: 52.5, 30: 50.6, 35: 47.3, 40: 45.4, 45: 43.5}

T_AIR = 50.0
T_PCB = 120.0      # the FR4 limit AN90003 marks on every curve
T_SIZE = 110.0     # sized to this, leaving 10 C for the plot reading and the stack interpolation


def interp(tab, x):
    ks = sorted(tab)
    if x < ks[0]:
        return None
    for a, b in zip(ks, ks[1:]):
        if x <= b:
            return tab[a] + (tab[b] - tab[a]) * (x - a) / (b - a)
    return tab[ks[-1]]


def rth_curve(t05, t1, x, p):
    """Rth(j-a) at side x and loss p, linear in p between the 0.5 W and 1 W curves (0.5 W alone below the 1 W range)."""
    t05x = interp(t05, x)
    if t05x is None:
        return None
    r05 = (t05x - 20.0) / 0.5
    t1x = interp(t1, x)
    if t1x is None:
        return r05
    r1 = (t1x - 20.0) / 1.0
    return r05 + (r1 - r05) * (p - 0.5) / 0.5


K_CU, K_FR4, T_FR4, R_BOARD = 385.0, 0.3, 1.6e-3, 0.1 / math.sqrt(math.pi)


def fin(x_mm, t_cu, h, r0, n=240):
    """Radial fin: copper disc of the square's area on FR4, surface coefficient h; returns K/W (general knowledge)."""
    a = x_mm * 1e-3 / math.sqrt(math.pi)
    rs = [r0 * (R_BOARD / r0) ** (i / n) for i in range(n + 1)]
    N = len(rs)
    lo, d, up, b = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
    for i in range(N):
        r_in = (rs[i - 1] + rs[i]) / 2 if i else rs[0]
        r_out = (rs[i] + rs[i + 1]) / 2 if i < N - 1 else rs[-1]
        d[i] += 2 * h * math.pi * (r_out ** 2 - r_in ** 2)
        if i < N - 1:
            rm = (rs[i] + rs[i + 1]) / 2
            g = 2 * math.pi * ((K_CU * t_cu if rm < a else 0.0) + K_FR4 * T_FR4) / math.log(rs[i + 1] / rs[i])
            d[i] += g
            up[i] -= g
            d[i + 1] += g
            lo[i + 1] -= g
    b[0] = 1.0
    for i in range(1, N):
        w = lo[i] / d[i - 1]
        d[i] -= w * up[i - 1]
        b[i] -= w * b[i - 1]
    th = b[-1] / d[-1]
    for i in range(N - 2, -1, -1):
        th = (b[i] - up[i] * th) / d[i]
    return th


_FIN = None


def fit_fin():
    global _FIN
    if _FIN is None:
        tgt = {x: (F25_05[x] - 20) / 0.5 for x in (6, 8, 10, 12, 14, 16, 20, 25, 30, 40, 50)}
        best = None
        for h in [8 + 0.5 * i for i in range(20)]:
            for r0 in [1.5e-3, 2.0e-3, 2.5e-3, 3.0e-3, 3.5e-3]:
                sp = {x: fin(x, 70e-6, h, r0) for x in tgt}
                rint = sum(tgt[x] - sp[x] for x in tgt) / len(tgt)
                err = math.sqrt(sum((tgt[x] - sp[x] - rint) ** 2 for x in tgt) / len(tgt))
                if best is None or err < best[0]:
                    best = (err, h, r0, rint)
        _FIN = best
    return _FIN


def rth_stack(x, p, t_um):
    """Rth(j-a) for an x mm square (the same on every stitched layer) with t_um of summed copper."""
    r70 = rth_curve(F25_05, F25_1, x, p)
    if r70 is None:
        return None
    if t_um >= 70:
        r280 = rth_curve(F35_05, F35_1, x, p)
        frac = min(math.log(t_um / 70) / math.log(4), 1.0)
        return r70 + (r280 - r70) * frac
    _, h, r0, rint = fit_fin()
    return r70 * (rint + fin(x, t_um * 1e-6, h, r0)) / (rint + fin(x, 70e-6, h, r0))


def coupling(x, p, t_um):
    """Extra rise from the other conducting FET ~2 mm away (Fig. 41, 0.5 W each), scaled to p and the stack's Rth."""
    one, two = interp(F41_ONE, x), interp(F41_TWO, x)
    if one is None:
        return None
    return (two - one) * (p / 0.5) * (rth_stack(x, p, t_um) / rth_stack(x, 0.5, 70))


def tj(x, p, t_um, neighbour=True, t_air=T_AIR):
    r = rth_stack(x, p, t_um)
    if r is None:
        return None
    c = coupling(x, p, t_um) if neighbour else 0.0
    if c is None:
        return None
    return t_air + p * r + c


def side(area_mm2):
    """The square the curves read for a pour: the side of a square of the same area on one layer."""
    return math.sqrt(area_mm2)
