"""layout_poe_pd.py: the poe_pd block's PCB layout (LT4294 + LT4321, 8 + 1 PSMN040-100MSE), 4 layers, made headless
with KiCad 10's pcbnew Python.

    "<KiCad>\\bin\\python.exe" layout_poe_pd.py prepare <poe_pd.kicad_pcb>   everything below, then zones filled
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py finish  <poe_pd.kicad_pcb>   refill zones only
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py copper  <poe_pd.kicad_pcb>   each conducting FET's tab copper per layer

Nothing is autorouted: every part, track, via and pour is written in this script (BLOCK.md section 9).

Outline 54 x 40 mm, 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu; PCBWay 4-layer 1 oz x 4), parts on the top side only
(Jeff, Ion-Speakers#15, 2026-11-19: PSMN040-100MSE bridge, 4 layers; the outline grown in Y from the 54 x 36 estimate
so the LT4321's fan-out fits). Arrangement, mm from the block's top-left corner (placed at ORIGIN):
  - Bridge, x 0-34, y 0-22: a BR_P column in the middle (x 13.4-21.0); the pair cells either side, PR12 over PR36
    on the left and PR45 over PR78 on the right (~10 x 11 mm each); a BR_N strip on each outer edge. Each top FET
    straddles its cell and the BR_P column (sources in the cell, tab in BR_P); each bottom FET straddles the BR_N
    strip and its cell (sources in BR_N, tab in the cell). Every pour is on all four layers and via-stitched, so each
    conducting FET's tab sits on its own ~9 mm square on every layer (calc/poe_pd_90w.py, copper rows). In1 joins
    the two BR_N strips with a band across the top.
  - Gate drives: bottom FETs on B.Cu down the BR_N strips, top FETs on In1 in the cell / BR_P gaps; senses PR12 and
    PR45 on In2 in the same gaps. All come down to the LT4321 (U12) below the bridge, which has a ring of fan-out vias
    5 mm out. Its pins run in roughly the reverse order of the bridge's signals, so the west group winds round it
    counter-clockwise (F.Cu: BG36, BG12; B.Cu: TG12, TG36, PR36; In2: PR12) and the east group clockwise (B.Cu: PR78,
    TG78, TG45, PR45; In1: BG45, BG78), each layer keeping its own order.
  - Bottom strip, y 22-40: U12 with C103 and its TVS D12; C100 and the choke L10, whose BR_P input sits on an F.Cu
    extension of the BR_P column. Under the bridge side, In1 is a BR_N plane and In2 a BR_P plane.
  - Right column, x 34.5-54: the PD. The VPORT square (Q58's tab, all layers) fed from L10.1 by an F.Cu leg that
    also carries the EN zener D13 (LT4321 Fig. 5) and C101; U10 with its class resistors, CPD C102 and TVS D10 next
    to it (LT4294 p11), CGATE; the POE_VDD pour from Q58's sources to C105; POE_VSS on F.Cu and both inner layers.
    The opto U11 sits across a 6 mm isolation band in the top-right corner, with the secondary (R106, the opto's
    outputs) in the corner itself.

Widths: 1.80 A worst case (90 W from 50 V): IPC-2221 external 10 C rise 1 oz ~0.64 mm, internal ~1.6 mm; the power
path is pours. Clearances (poe_pd.kicad_dru): POE_IN 0.6 mm (IPC-2221 Table 6-1 B2, 31-150 V) on every layer;
0.25 mm inside the LT4321/LT4294 fan-out areas and the FET courtyards; 6 mm secondary to primary.
"""
import sys

import pcbnew

ORIGIN = (100.0, 100.0)
W_PWR, W_SIG = 1.0, 0.25
VIA_BIG, VIA_SMALL = (0.8, 0.4), (0.6, 0.3)
OUTLINE = (0.0, 0.0, 54.0, 40.0)
LAYERS = ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')
LID = {'F.Cu': pcbnew.F_Cu, 'In1.Cu': pcbnew.In1_Cu, 'In2.Cu': pcbnew.In2_Cu, 'B.Cu': pcbnew.B_Cu}

BR_P, BR_N = '/PoE PD/BR_P', '/PoE PD/BR_N'
VPORT, VPIN = '/PoE PD/PD_VPORT', '/PoE PD/PD_VPIN'
VSS, VDD, PWRGD = 'POE_VSS', 'POE_VDD', 'PD_PWRGD'
P_ = lambda n: '/PoE PD/' + n
TG = lambda p: P_('PD_TG' + p)
BG = lambda p: P_('PD_BG' + p)
EN, HSG, CG, T2P, LED = P_('PD_BR_EN'), P_('PD_HSGATE'), P_('PD_CGATE'), P_('PD_T2P'), P_('T2P_LED_A')
POE_IN = {VDD, VSS, BR_P, BR_N, VPORT, VPIN, 'PR12', 'PR36', 'PR45', 'PR78'}

# --- bridge geometry ---------------------------------------------------------------------------------------
X_BRNL, X_CL, X_BRP, X_CR, X_BRNR, X_END = 0.5, 3.2, 13.4, 21.0, 31.2, 33.9
Y_TOP, Y_MID, Y_BR = 0.5, 11.3, 22.1
ROW_Y = (5.9, 16.7)
# (pair, cell x0, x1, y0, y1, top FET, bottom FET, top centre x, bottom centre x, rotation)
CELLS = [('PR12', X_CL, X_BRP, Y_TOP, Y_MID, 'Q50', 'Q54', 14.2, 4.0, 0),
         ('PR36', X_CL, X_BRP, Y_MID, Y_BR, 'Q51', 'Q55', 14.2, 4.0, 0),
         ('PR45', X_CR, X_BRNR, Y_TOP, Y_MID, 'Q52', 'Q56', 20.2, 30.4, 180),
         ('PR78', X_CR, X_BRNR, Y_MID, Y_BR, 'Q53', 'Q57', 20.2, 30.4, 180)]

PLACE = {
    # bottom strip, bridge side of the choke: the LT4321 (U12) with its CPD (C103) and TVS (D12), C100 at the choke
    'U12': (12.0, 31.0, 90), 'C103': (9.0, 25.6, 180), 'D12': (4.0, 37.0, 0), 'C100': (18.25, 31.5, 270),
    # the choke, its output cap C101, the EN zener D13 (LT4321 Fig. 5) on the VPORT leg, then C105 (the output and
    # the POE_VDD / POE_VSS ports)
    'L10': (24.5, 31.5, 270), 'C101': (31.0, 25.6, 270), 'D13': (25.6, 23.6, 180), 'C105': (37.7, 33.0, 180),
    # PD: Q58 (tab on the VPORT square), U10 with RCLS / RCLS++ on its right, its CPD (C102) and TVS (D10) next to
    # it (LT4294 p11: "strictly required ... as close to the LT4294 as possible")
    'Q58': (41.0, 21.5, 90),
    'U10': (48.6, 16.6, 180), 'R102': (52.3, 14.9, 90), 'R101': (52.3, 18.4, 270),
    'C102': (48.9, 19.65, 0), 'R100': (44.8, 19.65, 0), 'TP41': (45.2, 15.6, 0),
    'D10': (48.2, 23.4, 0), 'R103': (52.6, 23.4, 270), 'C104': (52.4, 28.1, 270),
    'R105': (47.6, 28.4, 0), 'TP40': (48.0, 32.6, 0),
    'U11': (50.0, 6.6, 90), 'R106': (45.6, 2.0, 0),
}
for _pr, _x0, _x1, _y0, _y1, _qt, _qb, _xt, _xb, _rot in CELLS:
    _yc = (_y0 + _y1) / 2
    PLACE[_qt] = (_xt, _yc, _rot)
    PLACE[_qb] = (_xb, _yc, _rot)

Y_BOT = OUTLINE[3] - 0.5

# --- isolation barrier (6 mm) around the secondary corner ---------------------------------------------------
SEC = (44.0, 0.0, 54.0, 3.6)           # the secondary corner: R106 and U11's outputs
BAND = [(38.0, 0.0), (44.0, 0.0), (44.0, 3.6), (54.0, 3.6), (54.0, 9.6), (38.0, 9.6)]

# --- PD pours ---------------------------------------------------------------------------------------------------
SQ_VPORT = (34.5, 12.4, 44.5, 22.1)     # Q58's tab copper, every layer
TAB_D10 = (44.5, 20.4, 46.6, 24.4)      # VPORT on to D10's pad 1 (F.Cu)
# L10.1 (VPORT) up to a band under the bridge and along it to the square, F.Cu only
LEG_VPORT = [(26.8, 22.7), (34.5, 22.7), (34.5, 12.4), (36.0, 12.4), (36.0, 24.5), (29.9, 24.5), (29.9, 30.0),
             (26.8, 30.0)]
R_VDD = [(37.6, 22.7), (44.5, 22.7), (44.5, 35.2), (37.6, 35.2)]      # Q58's sources to C105.1 (F.Cu, B.Cu)
X_CMC = 23.0                            # inner planes: bridge side (BR_N / BR_P) left of this, POE_VSS right
R_VSS = [(X_CMC + 0.5, 25.1), (34.2, 25.1), (34.2, 0.5), (38.0, 0.5), (38.0, 9.6), (53.5, 9.6), (53.5, Y_BOT),
         (X_CMC + 0.5, Y_BOT)]
R_VSS_IN = [(X_CMC + 0.5, 22.4), (34.2, 22.4), (34.2, 0.5), (38.0, 0.5), (38.0, 9.6), (53.5, 9.6), (53.5, Y_BOT),
            (X_CMC + 0.5, Y_BOT)]
# The BR_P column carried on down F.Cu to L10.2 (the choke's BR_P input)
EXT_BRP = (18.6, Y_BR, X_CR, 28.6)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# In1: the two BR_N strips joined by a band across the top of the bridge, and the BR_N plane under the bridge side
# of the bottom strip. In2: the BR_P column and the BR_P plane there. Both planes carry no signal.
Y_BAND = 1.9
IN1_BRN = [(X_BRNL, Y_TOP), (X_END, Y_TOP), (X_END, Y_BR), (X_BRNR, Y_BR), (X_BRNR, Y_BAND), (X_CL, Y_BAND),
           (X_CL, Y_BR), (X_BRNL, Y_BR)]
BOTTOM = rect(X_BRNL, Y_BR, X_CMC, Y_BOT)

# Pours: (net, priority, polygon, layers). Overlapping pours of one net get different priorities.
ZONES = [
    (BR_N, 3, rect(X_BRNL, Y_TOP, X_CL, Y_BR), ('F.Cu', 'In2.Cu', 'B.Cu')),
    (BR_N, 3, rect(X_BRNR, Y_TOP, X_END, Y_BR), ('F.Cu', 'In2.Cu', 'B.Cu')),
    (BR_P, 3, rect(X_BRP, Y_TOP, X_CR, Y_BR), ('F.Cu', 'In1.Cu', 'B.Cu')),
    (BR_P, 4, rect(*EXT_BRP), ('F.Cu',)),
    (BR_N, 4, IN1_BRN, ('In1.Cu',)),
    (BR_P, 4, rect(X_BRP, Y_TOP, X_CR, Y_BR), ('In2.Cu',)),
    (BR_N, 2, BOTTOM, ('In1.Cu',)),
    (BR_P, 2, BOTTOM, ('In2.Cu',)),
    (VPORT, 3, rect(*SQ_VPORT), LAYERS),
    (VPORT, 4, rect(*TAB_D10), ('F.Cu',)),
    (VPORT, 2, LEG_VPORT, ('F.Cu',)),
    (VDD, 3, R_VDD, ('F.Cu',)),
    (VDD, 3, R_VDD, ('B.Cu',)),
    (VSS, 1, R_VSS_IN, ('In1.Cu', 'In2.Cu')),
    (VSS, 1, R_VSS, ('F.Cu', 'B.Cu')),
] + [(pr, 3, rect(x0, y0, x1, y1), LAYERS) for pr, x0, x1, y0, y1, *_ in CELLS]

TRACKS = []     # (net, layer, width, [points]) - points are (x, y) or ('ref', 'pad')
VIAS = []       # (net, (x, y), big)


def T(net, layer, width, *pts):
    TRACKS.append((net, layer, width, list(pts)))


def V(net, at, big=None):
    VIAS.append((net, at, big))


# ============================================================================================================
# Routes: every fan-out from a fine-pitch part, every gate and sense from the bridge to the LT4321, and the PD's
# signals. Points are mm from the block corner, or ('ref', 'pad') for a pad centre. Nothing is autorouted.
# ============================================================================================================
import math  # noqa: E402

S = lambda r, n: (r, n)
SM = False          # small via (0.6 / 0.3) on a POE_IN net: the senses and the fine-pitch fan-out

# --- bridge: gate drives and senses out of the cells -------------------------------------------------------------
# Bottom FETs, left: gate -> F.Cu stub -> via -> B.Cu down the BR_N strip (BG12 outside at x 0.95, BG36 inside at
# x 2.0) -> via at the strip's foot -> F.Cu to U12's ring.
T(BG('12'), 'F.Cu', W_SIG, S('Q54', '4'), (0.95, 7.7)); V(BG('12'), (0.95, 7.7))
T(BG('12'), 'B.Cu', W_SIG, (0.95, 7.7), (0.95, 23.2)); V(BG('12'), (0.95, 23.2))
T(BG('36'), 'F.Cu', W_SIG, S('Q55', '4'), (2.0, 18.6)); V(BG('36'), (2.0, 18.6))
T(BG('36'), 'B.Cu', W_SIG, (2.0, 18.6), (2.0, 23.2)); V(BG('36'), (2.0, 23.2))
# Bottom FETs, right: the same down the right strip (BG45 inside at x 32.75, BG78 outside at x 33.5), then In1
# lanes west under the choke to U12's ring.
T(BG('45'), 'F.Cu', W_SIG, S('Q56', '4'), (32.75, 4.0)); V(BG('45'), (32.75, 4.0))
T(BG('45'), 'B.Cu', W_SIG, (32.75, 4.0), (32.75, 23.2)); V(BG('45'), (32.75, 23.2))
T(BG('78'), 'F.Cu', W_SIG, S('Q57', '4'), (33.5, 15.1)); V(BG('78'), (33.5, 15.1))
T(BG('78'), 'B.Cu', W_SIG, (33.5, 15.1), (33.5, 23.2)); V(BG('78'), (33.5, 23.2))
# Top FETs: gate -> via in the cell -> In1 down the cell / BR_P gap -> exit via below the bridge.
T(TG('12'), 'F.Cu', W_SIG, S('Q50', '4'), (12.67, 8.15)); V(TG('12'), (12.67, 8.15))
T(TG('12'), 'In1.Cu', W_SIG, (12.67, 8.15), (13.35, 8.85), (13.35, 23.3), (13.6, 23.9)); V(TG('12'), (13.6, 23.9))
T(TG('36'), 'F.Cu', W_SIG, S('Q51', '4'), (12.67, 18.95)); V(TG('36'), (12.67, 18.95))
T(TG('36'), 'In1.Cu', W_SIG, (12.67, 18.95), (12.6, 19.1), (12.6, 23.0)); V(TG('36'), (12.6, 23.0))
T(TG('45'), 'F.Cu', W_SIG, S('Q52', '4'), (21.73, 3.65)); V(TG('45'), (21.73, 3.65))
T(TG('45'), 'In1.Cu', W_SIG, (21.73, 3.65), (22.35, 4.25), (22.35, 25.95), (22.6, 26.2)); V(TG('45'), (22.6, 26.2))
T(TG('78'), 'F.Cu', W_SIG, S('Q53', '4'), (21.73, 14.45)); V(TG('78'), (21.73, 14.45))
T(TG('78'), 'In1.Cu', W_SIG, (21.73, 14.45), (21.5, 14.7), (21.5, 25.3), (21.6, 25.4)); V(TG('78'), (21.6, 25.4))
# Senses: PR12 from a small via in its cell, on In2 down the gap and on to U12's ring (the only signal in the In2
# BR_P plane); PR45 likewise to an exit via; PR36 and PR78 straight off their cells' bottoms on B.Cu.
V('PR12', (11.9, 10.2), SM)
V('PR45', (23.2, 10.2), SM)
T('PR45', 'In2.Cu', W_SIG, (23.2, 10.2), (23.2, 25.1), (24.0, 25.9)); V('PR45', (24.0, 25.9), SM)

# --- U12 (LT4321) fan-out: F.Cu stubs from every pin to a ring of vias 5 mm out, in pin order -------------------
UX, UY = PLACE['U12'][:2]
RING = {'13': (BG('36'), 140), '14': (BG('12'), 165), '15': ('PR12', 190), '16': (TG('12'), 215),
        '1': (TG('36'), 235), '2': ('PR36', 255), '3': ('PR45', 275), '4': (TG('45'), 295),
        '5': (TG('78'), 325), '6': ('PR78', 350), '7': (BG('78'), 15), '8': (BG('45'), 40)}
OUT = {}
for _p in ('13', '14', '15', '16'):
    OUT[_p] = (-1, 0)
for _p in ('1', '2', '3', '4'):
    OUT[_p] = (0, 1)
for _p in ('5', '6', '7', '8'):
    OUT[_p] = (1, 0)
# pin centres of U12 at rotation 90 (pins 1-4 bottom, 5-8 right, 9-12 top, 13-16 left), from the footprint
_PIN = {'1': (-0.98, 1.84), '2': (-0.32, 1.84), '3': (0.32, 1.84), '4': (0.98, 1.84),
        '5': (1.84, 0.97), '6': (1.84, 0.32), '7': (1.84, -0.32), '8': (1.84, -0.98),
        '13': (-1.84, -0.98), '14': (-1.84, -0.32), '15': (-1.84, 0.32), '16': (-1.84, 0.97)}
RV = {}
for _p, (_net, _a) in RING.items():
    _vx = round(UX + 5.0 * math.cos(math.radians(_a)), 2)
    _vy = round(UY - 5.0 * math.sin(math.radians(_a)), 2)
    RV[_net] = (_vx, _vy)
    _px, _py = UX + _PIN[_p][0], UY + _PIN[_p][1]
    _dx, _dy = OUT[_p]
    T(_net, 'F.Cu', 0.2, S('U12', _p), (round(_px + _dx * 0.9, 2), round(_py + _dy * 0.9, 2)), (_vx, _vy))
    if _net not in (BG('36'), BG('12')):          # these two arrive on F.Cu: no via
        V(_net, (_vx, _vy), SM if _net.startswith('PR') else None)
# top: OUTP (12) and ~EN (10) to BR_P vias (In2), EN (11) up the middle to its via, OUTN (9) into the exposed pad
# and to a BR_N via (In1); C103 (CPD at the LT4321) right above
T(BR_P, 'F.Cu', 0.2, S('U12', '12'), (11.02, UY - 2.5), (10.7, UY - 3.6)); V(BR_P, (10.7, UY - 3.6), SM)
T(BR_P, 'F.Cu', 0.4, (10.7, UY - 3.6), ('C103', '1'))
T(EN, 'F.Cu', W_SIG, S('U12', '11'), (11.68, UY - 4.7)); V(EN, (11.68, UY - 4.7))
T(BR_P, 'F.Cu', 0.2, S('U12', '10'), (12.32, UY - 2.5), (12.6, UY - 3.6)); V(BR_P, (12.6, UY - 3.6), SM)
T(BR_N, 'F.Cu', 0.2, (12.95, UY - 1.4), (12.95, UY - 0.8))                               # pin 9 into the exposed pad
T(BR_N, 'F.Cu', 0.2, S('U12', '9'), (12.98, UY - 2.5), (13.9, UY - 3.2)); V(BR_N, (13.9, UY - 3.2), SM)
V(BR_N, (8.4, 26.3)); T(BR_N, 'F.Cu', 0.6, ('C103', '2'), (8.4, 26.3))

# --- U12's signals from the bridge to the ring ------------------------------------------------------------------
# The LT4321's pins run in roughly the reverse order of the bridge's signals, so the two groups wind round U12 the
# opposite ways, each layer keeping its own order: west side CCW (B.Cu: TG12 inside, TG36, PR36 outside; F.Cu:
# BG36, BG12), east side CW (B.Cu: PR78 inside, TG78, TG45, PR45 outside; In1: BG45, BG78).
T(BG('36'), 'F.Cu', W_SIG, (2.0, 23.2), (3.0, 24.2), (5.5, 27.3), (7.6, 27.3), RV[BG('36')])
T(BG('12'), 'F.Cu', W_SIG, (0.95, 23.2), (0.95, 29.0), (1.66, 29.71), RV[BG('12')])
T('PR12', 'In2.Cu', W_SIG, (11.9, 10.2), (11.9, 21.9), (9.3, 24.5), (9.3, 28.6), (7.6, 31.3), RV['PR12'])
T(TG('12'), 'B.Cu', W_SIG, (13.6, 23.9), (13.6, 24.8), (6.6, 24.8), (6.0, 25.4), (6.0, 33.2), (6.67, 33.87),
  RV[TG('12')])
T(TG('36'), 'B.Cu', W_SIG, (12.6, 23.0), (12.6, 24.1), (5.9, 24.1), (5.4, 24.6), (5.4, 34.5), (6.0, 35.1),
  RV[TG('36')])
T('PR36', 'B.Cu', W_SIG, (9.5, 21.5), (9.5, 23.2), (5.0, 23.2), (4.55, 23.65), (4.55, 35.85), (5.0, 36.3),
  (10.24, 36.3), RV['PR36'])
T('PR78', 'B.Cu', W_SIG, (26.0, 21.5), (26.0, 24.0), (20.9, 24.0), (20.5, 24.4), (20.5, 28.3), (17.2, 31.6),
  RV['PR78'])
T(TG('78'), 'B.Cu', W_SIG, (21.6, 25.4), (21.6, 29.3), (17.6, 33.3), (16.67, 33.87), RV[TG('78')])
T(TG('45'), 'B.Cu', W_SIG, (22.6, 26.2), (22.6, 31.3), (17.8, 36.1), (14.68, 36.1), RV[TG('45')])
T('PR45', 'B.Cu', W_SIG, (24.0, 25.9), (24.0, 33.0), (23.3, 37.9), (13.2, 37.9), (12.44, 37.14), RV['PR45'])
T(BG('45'), 'In1.Cu', W_SIG, (32.75, 23.2), (32.75, 28.9), (17.5, 28.9), (16.6, 28.0), RV[BG('45')])
T(BG('78'), 'In1.Cu', W_SIG, (33.5, 23.2), (33.5, 29.6), (17.0, 29.6), RV[BG('78')])
# EN: from the zener D13 (its VPORT pad on the leg) on B.Cu, above PR78's lane, to U12's EN via
V(EN, (24.6, 22.75)); T(EN, 'F.Cu', W_SIG, ('D13', '2'), (24.6, 22.75))
T(EN, 'B.Cu', W_SIG, (24.6, 22.75), (24.45, 22.9), (14.6, 22.9), (14.6, 25.0), (12.2, 26.3), (11.68, 26.3))

# D12 (the LT4321's TVS) and the choke: L10.2 sits on the F.Cu BR_P extension; L10.3, C100 and D12 down to In1/In2
for _x in (1.0, 2.5):
    V(BR_P, (_x, 39.0)); T(BR_P, 'F.Cu', 0.8, ('D12', '1'), (_x, 39.0))
for _x in (5.5, 7.0):
    V(BR_N, (_x, 39.0)); T(BR_N, 'F.Cu', 0.8, ('D12', '2'), (_x, 39.0))
for _x in (20.0, 21.4):
    V(BR_N, (_x, 36.7)); T(BR_N, 'F.Cu', 1.0, ('L10', '3'), (_x, 36.7))
T(BR_P, 'F.Cu', 0.4, ('C100', '1'), (19.6, 29.6))                         # C100 between the choke's inputs
T(BR_N, 'F.Cu', 0.4, ('C100', '2'), (19.6, 33.4))
# BR_N vias in each piece of the strips' F.Cu that a gate stub cuts off
for _at in ((2.4, 2.2), (2.5, 12.0), (32.2, 1.6), (31.6, 10.5), (31.6, 20.6)):
    V(BR_N, _at, True)
# C101's POE_VSS pad to In1 / In2
V(VSS, (31.0, 27.4)); T(VSS, 'F.Cu', 0.5, ('C101', '2'), (31.0, 27.4))

# --- PD: U10 (LT4294) fan-out and the short signals --------------------------------------------------------------
T(P_('PD_RCLSPP'), 'F.Cu', 0.2, S('U10', '4'), (51.0, 16.1), ('R102', '1'))
T(P_('PD_RCLS'), 'F.Cu', 0.2, S('U10', '3'), (51.2, 16.6), ('R101', '1'))
T(T2P, 'F.Cu', 0.2, S('U10', '6'), (46.3, 15.6), (46.3, 13.9), (49.9, 13.9), (50.6, 13.2), (50.6, 12.36),
  ('U11', '2'))
T(PWRGD, 'F.Cu', 0.2, S('U10', '7'), (45.7, 16.1), ('TP41', '1'))
T(VDD, 'F.Cu', 0.2, S('U10', '8'), (45.3, 16.6), (44.9, 17.2)); V(VDD, (44.9, 17.2), SM)
T(VDD, 'In1.Cu', W_SIG, (44.9, 17.2), (44.9, 22.4), (44.3, 23.0), (43.6, 23.0)); V(VDD, (43.6, 23.0), SM)
T(VDD, 'F.Cu', 0.5, (44.2, 28.4), ('R105', '1'))                          # R105 from the VDD pour
T(HSG, 'F.Cu', 0.2, S('U10', '9'), (46.2, 17.1), (46.0, 18.2)); V(HSG, (46.0, 18.2))
T(HSG, 'F.Cu', W_SIG, S('Q58', '4'), (42.0, 24.15)); V(HSG, (42.0, 24.15))
T(HSG, 'B.Cu', W_SIG, (46.0, 18.2), (46.0, 24.15), (42.0, 24.15))
T(HSG, 'F.Cu', W_SIG, ('R103', '1'), (52.6, 21.6)); V(HSG, (52.6, 21.6))
T(HSG, 'B.Cu', W_SIG, (52.6, 21.6), (46.0, 21.6))
T(CG, 'F.Cu', W_SIG, ('R103', '2'), ('C104', '1'))
T(VPIN, 'F.Cu', 0.2, S('U10', '10'), (46.9, 17.9), (46.9, 19.0))
T(VPIN, 'F.Cu', 0.5, ('R100', '2'), ('C102', '1'))
T(VSS, 'F.Cu', 0.2, S('U10', '1'), (49.4, 17.6)); T(VSS, 'F.Cu', 0.2, S('U10', '5'), (49.4, 15.6))
T(LED, 'F.Cu', W_SIG, S('U11', '1'), (48.73, 12.95)); V(LED, (48.73, 12.95))
T(LED, 'In2.Cu', W_SIG, (48.73, 12.95), (48.73, 26.6), (49.06, 26.9)); V(LED, (49.06, 26.9))
T(LED, 'F.Cu', W_SIG, (49.06, 26.9), ('R105', '2'))
# the secondary corner
T('POE_T2P_N', 'F.Cu', W_SIG, ('R106', '2'), ('U11', '4'))



# Stitching and thermal vias, 0.8 / 0.4 mm on a grid, kept clear of every pad, track and via of another net
# (stitch() below): (net, rectangle, pitch)
STITCH = [(pr, (x0 + 0.9, y0 + 0.9, x1 - 0.9, y1 - 0.9), 2.5) for pr, x0, x1, y0, y1, *_ in CELLS] + [
    (BR_P, (X_BRP + 0.9, Y_TOP + 0.9, X_CR - 0.9, Y_BR - 0.9), 2.5),
    (BR_N, (X_BRNL + 0.8, Y_TOP + 0.8, X_CL - 0.8, Y_BR - 0.8), 2.5),
    (BR_N, (X_BRNR + 0.8, Y_TOP + 0.8, X_END - 0.8, Y_BR - 0.8), 2.5),
    (VPORT, (SQ_VPORT[0] + 0.9, SQ_VPORT[1] + 0.9, SQ_VPORT[2] - 0.9, SQ_VPORT[3] - 0.9), 2.5),
    (VDD, (38.4, 23.6, 43.8, 34.6), 2.5),
    (VSS, (24.5, 35.6, 53.0, Y_BOT - 0.6), 3.0),
    (VSS, (45.6, 10.6, 53.0, 30.0), 3.0),
]


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


def at(board, p):
    if isinstance(p[0], str):
        q = board.FindFootprintByReference(p[0]).FindPadByNumber(p[1]).GetPosition()
        return pcbnew.ToMM(q.x) - ORIGIN[0], pcbnew.ToMM(q.y) - ORIGIN[1]
    return p


def set_layers(board):
    if board.GetCopperLayerCount() != 4:
        board.SetCopperLayerCount(4)
        board.GetDesignSettings().SetCopperLayerCount(4)


def clear(board):
    for t in list(board.GetTracks()):
        board.Delete(t)
    for z in list(board.Zones()):
        board.Delete(z)
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(d)


def place(board):
    for ref, (x, y, rot) in PLACE.items():
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise SystemExit(f'{ref} is not on the board (run pcb-update-pcb.ps1 on the block folder first)')
        fp.SetLocked(False)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        fp.SetLocked(True)
        for field in fp.GetFields():
            if field.GetName() not in ('Reference', 'Value'):
                field.SetVisible(False)
        fp.Value().SetVisible(False)
    missing = {fp.GetReference() for fp in board.GetFootprints()} - set(PLACE)
    if missing:
        raise SystemExit('no position for: ' + ' '.join(sorted(missing)))


def place_refs(board):
    """Designators on the silkscreen, readable and off pads (as in pcb-blocks#2's script)."""
    def grow(box, mm):
        b = pcbnew.BOX2I(box.GetPosition(), box.GetSize())
        b.Inflate(pcbnew.FromMM(mm))
        return b

    fps = sorted(board.GetFootprints(), key=lambda f: f.GetReference())
    pads = [grow(p.GetBoundingBox(), 0.2) for f in fps for p in f.Pads()]
    crt = {f.GetReference(): f.GetCourtyard(pcbnew.F_CrtYd).BBox() for f in fps}
    body = {r: grow(b, -0.4) for r, b in crt.items()}
    x0, y0, x1, y1 = OUTLINE
    edge = pcbnew.BOX2I(P(x0 + 0.3, y0 + 0.3), pcbnew.VECTOR2I(pcbnew.FromMM(x1 - x0 - 0.6), pcbnew.FromMM(y1 - y0 - 0.6)))
    placed, unplaced = [], []
    own_silk = {f.GetReference(): [grow(g.GetBoundingBox(), 0.1) for g in f.GraphicalItems()
                                   if g.GetLayer() == pcbnew.F_SilkS] for f in fps}
    mm = pcbnew.FromMM
    for f in fps:
        t = f.Reference()
        t.SetVisible(True)
        c = crt[f.GetReference()]
        cx, cy = c.GetCenter().x, c.GetCenter().y
        spots = [(cx, cy)]
        for d in (0.6, 1.2, 2.0):
            for s in (0, -1.5, 1.5, -3.0, 3.0):
                spots += [(cx + mm(s), c.GetTop() - mm(d)), (cx + mm(s), c.GetBottom() + mm(d))]
            for s in (0, -1.5, 1.5):
                spots += [(c.GetLeft() - mm(d + 1.2), cy + mm(s)), (c.GetRight() + mm(d + 1.2), cy + mm(s))]
        ok = False
        for size in (1.0, 0.8):
            t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
            t.SetTextThickness(mm(0.15))
            for angle in (0, 90):
                for sx, sy in spots:
                    t.SetTextAngleDegrees(angle)
                    t.SetPosition(pcbnew.VECTOR2I(int(sx), int(sy)))
                    box = grow(t.GetBoundingBox(), 0.15)
                    if not edge.Contains(box):
                        continue
                    if any(box.Intersects(p) for p in pads) or any(box.Intersects(b) for b in placed):
                        continue
                    if any(box.Intersects(b) for r, b in body.items() if r != f.GetReference()):
                        continue
                    if any(box.Intersects(b) for b in own_silk[f.GetReference()]):
                        continue
                    placed.append(box)
                    ok = True
                    break
                if ok:
                    break
            if ok:
                break
        if not ok:
            t.SetVisible(False)
            unplaced.append(f.GetReference())
    return unplaced


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        raise SystemExit(f'no net {name}')
    return n


def track(board, name, layer, width, pts):
    pts = [at(board, p) for p in pts]
    for a, b in zip(pts, pts[1:]):
        if a == b:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(board.GetLayerID(layer))
        t.SetNet(net(board, name))
        t.SetLocked(True)
        board.Add(t)


def via(board, name, p, big=None):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(*at(board, p)))
    d, h = VIA_BIG if (big or (big is None and name in POE_IN)) else VIA_SMALL
    v.SetWidth(pcbnew.FromMM(d))
    v.SetDrill(pcbnew.FromMM(h))
    v.SetNet(net(board, name))
    v.SetLocked(True)
    board.Add(v)


def polygon(points):
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in points:
        chain.Append(P(x, y))
    chain.SetClosed(True)
    return chain


def lset(names):
    ls = pcbnew.LSET()
    for n in names:
        ls.AddLayer(LID[n])
    return ls


def outline(board):
    x0, y0, x1, y1 = OUTLINE
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)


def rule_area(board, name, pts, keepout, layers=LAYERS):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(keepout)
    z.SetDoNotAllowVias(keepout)
    z.SetDoNotAllowZoneFills(keepout and name.startswith('isolation'))
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.SetLayerSet(lset(layers))
    z.SetZoneName(name)
    z.Outline().AddOutline(polygon(pts))
    z.SetLocked(True)
    board.Add(z)


def pours(board):
    for name, prio, pts, layers in ZONES:
        for layer in layers:
            z = pcbnew.ZONE(board)
            z.SetLayer(LID[layer])
            z.SetNet(net(board, name))
            z.SetAssignedPriority(prio)
            z.SetMinThickness(pcbnew.FromMM(0.25))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetZoneName(f'{name.split("/")[-1]} pour')
            z.Outline().AddOutline(polygon(pts))
            z.SetLocked(True)
            board.Add(z)


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def stitch(board):
    """Add the STITCH grid vias that keep clear of everything else: 0.6 mm (POE_IN) from other nets' pads, tracks
    and vias, never in a pad, inside the outline, and outside the barrier and the secondary corner."""
    mm = pcbnew.ToMM
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append((p.GetNetname(), mm(bb.GetLeft()) - ORIGIN[0], mm(bb.GetTop()) - ORIGIN[1],
                         mm(bb.GetRight()) - ORIGIN[0], mm(bb.GetBottom()) - ORIGIN[1]))
    segs, vias = [], []
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition()
            vias.append((t.GetNetname(), (mm(q.x) - ORIGIN[0], mm(q.y) - ORIGIN[1]), mm(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            a, b = t.GetStart(), t.GetEnd()
            segs.append((t.GetNetname(), (mm(a.x) - ORIGIN[0], mm(a.y) - ORIGIN[1]),
                         (mm(b.x) - ORIGIN[0], mm(b.y) - ORIGIN[1]), mm(t.GetWidth()) / 2))
    r = VIA_BIG[0] / 2
    added = 0
    x0b, y0b, x1b, y1b = OUTLINE
    for name, (x0, y0, x1, y1), pitch in STITCH:
        placed = []
        y = y0
        while y <= y1 + 1e-6:
            x = x0
            while x <= x1 + 1e-6:
                p = (round(x, 2), round(y, 2))
                ok = x0b + 0.8 <= p[0] <= x1b - 0.8 and y0b + 0.8 <= p[1] <= y1b - 0.8
                ok = ok and not (p[1] < 9.6 + r + 0.3 and p[0] > 38.0 - r - 0.3)          # barrier / secondary
                for pn, l, t_, rr, b_ in pads if ok else []:
                    dx = max(l - p[0], 0, p[0] - rr)
                    dy = max(t_ - p[1], 0, p[1] - b_)
                    d = (dx * dx + dy * dy) ** 0.5
                    if d < r + (0.25 if pn == name else 0.65):
                        ok = False
                        break
                for sn, a, b, w in segs if ok else []:
                    if sn != name and _seg_dist(p, a, b) < r + w + 0.65:
                        ok = False
                        break
                for vn, q, vr in (vias + placed) if ok else []:
                    if ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 < r + vr + (0.65 if vn != name else 0.35):
                        ok = False
                        break
                if ok:
                    via(board, name, p, True)
                    placed.append((name, p, r))
                    added += 1
                x += pitch
            y += pitch
        vias += placed
    return added


def build(path):
    board = pcbnew.LoadBoard(path)
    set_layers(board)
    clear(board)
    place(board)
    outline(board)
    hidden = place_refs(board)
    if hidden:
        print('designators with no clear spot (hidden on silk, kept on F.Fab):', ' '.join(hidden))
    for name, layer, width, pts in TRACKS:
        track(board, name, layer, width, pts)
    for name, p, big in VIAS:
        via(board, name, p, big)
    rule_area(board, 'isolation barrier 6 mm', BAND, True)
    ux, uy = PLACE['U12'][:2]
    rule_area(board, 'FANOUT_U12', rect(ux - 5.6, uy - 5.6, ux + 5.6, uy + 5.6), False)
    ux, uy = PLACE['U10'][:2]
    rule_area(board, 'FANOUT_U10', rect(ux - 3.6, uy - 3.6, ux + 3.6, uy + 3.6), False)
    n_stitch = stitch(board)
    pours(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'{path}: {len(PLACE)} parts placed and locked, {len(TRACKS)} hand track runs, {len(VIAS)} hand vias, '
          f'{n_stitch} stitching vias, {len(ZONES)} pours; zones filled')


def prepare(path):
    build(path)


def finish(path):
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'zones filled: {path}')


# Conducting FETs in the one-pair-set worst case (calc/poe_pd_90w.py): every top FET (one at a time, on the shared
# BR_P column), every bottom FET (on its own cell), and Q58. (ref, label, neighbour within ~2 mm conducting)
COPPER_FETS = [('Q50', 'Q50-Q53 top (BR_P column, shared)'), ('Q54', 'Q54 bottom, PR12 cell'),
               ('Q55', 'Q55 bottom, PR36 cell'), ('Q56', 'Q56 bottom, PR45 cell'), ('Q57', 'Q57 bottom, PR78 cell'),
               ('Q58', 'Q58 hot-swap (VPORT square)')]
WINDOW = 14.0


def copper(path):
    """For each FET, its tab net's filled copper on each layer within a WINDOW mm square centred on the tab."""
    board = pcbnew.LoadBoard(path)
    out = []
    for ref, label in COPPER_FETS + [('Q51', 'Q51'), ('Q52', 'Q52'), ('Q53', 'Q53')]:
        pad = board.FindFootprintByReference(ref).FindPadByNumber('5')
        c = pad.GetPosition()
        h = pcbnew.FromMM(WINDOW / 2)
        win = pcbnew.SHAPE_POLY_SET()
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h)):
            chain.Append(pcbnew.VECTOR2I(c.x + dx, c.y + dy))
        chain.SetClosed(True)
        win.AddOutline(chain)
        areas = {}
        for name in LAYERS:
            lid = board.GetLayerID(name)
            cu = pcbnew.SHAPE_POLY_SET()
            for z in board.Zones():
                if z.GetIsRuleArea() or z.GetNetCode() != pad.GetNetCode() or not z.IsOnLayer(lid):
                    continue
                cu.BooleanAdd(z.GetFilledPolysList(lid))
            cu.BooleanIntersection(win)
            areas[name] = cu.Area() / 1e12
        out.append((ref, label, areas))
        print(f"    ('{label}', {{" + ', '.join(f"'{k}': {v:.0f}" for k, v in areas.items()) + '}),')
    return out


if __name__ == '__main__':
    modes = {'prepare': prepare, 'finish': finish, 'copper': copper}
    if len(sys.argv) != 3 or sys.argv[1] not in modes:
        raise SystemExit(__doc__)
    modes[sys.argv[1]](sys.argv[2])
