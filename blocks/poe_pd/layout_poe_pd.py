"""layout_poe_pd.py: the poe_pd block's PCB layout (LT4294 + LT4321, 8 + 1 PSMN040-100MSE), 4 layers, made headless
with KiCad 10's pcbnew Python.

    "<KiCad>\\bin\\python.exe" layout_poe_pd.py prepare <poe_pd.kicad_pcb>   everything below, then zones filled
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py finish  <poe_pd.kicad_pcb>   refill zones only
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py copper  <poe_pd.kicad_pcb>   each conducting FET's tab copper per layer
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py route   <poe_pd.kicad_pcb>   re-run Freerouting, rewrite the frozen runs

Placement, pours, stitching, every fan-out from a fine-pitch part and every gate / sense escape from the bridge are
written in this script. The longer signal runs between those vias (gate drives, senses, EN, HSGATE, the VDD sense,
the opto LED) were routed once by Freerouting 2.5.0 and are frozen as data in layout_poe_pd_routes.py, so prepare
gives the same board every time (BLOCK.md section 9).

Outline 54 x 36 mm, 4 layers (F.Cu, In1.Cu, In2.Cu, B.Cu; PCBWay 4-layer 1 oz x 4), parts on the top side only
(Jeff, Ion-Speakers#15, 2026-11-19: PSMN040-100MSE bridge, 4 layers, 54 x 36 mm). Arrangement, mm from the block's
top-left corner (placed at ORIGIN):
  - Bridge, x 0-34, y 0-22: a BR_P column in the middle (x 13.4-21.0); the pair cells either side, PR12 over PR36
    on the left and PR45 over PR78 on the right (each ~10 x 11 mm); a BR_N strip on each outer edge. Each top FET
    straddles its cell and the BR_P column (sources in the cell, tab in BR_P); each bottom FET straddles the BR_N
    strip and its cell (sources in BR_N, tab in the cell). Every pour is on all four layers, via-stitched, so each
    conducting FET's tab sits on its own ~9-10 mm square on every layer (calc/poe_pd_90w.py, copper rows).
  - Gate drives run on B.Cu (bottom FETs, along the BR_N strips) and In1.Cu (top FETs, in the cell/BR_P gaps);
    the pair senses on In2.Cu in the same gaps. All of them come down to the LT4321 below the bridge.
  - Bottom strip, y 22-36: the LT4321 (U12) with C103 and its TVS D12, then the choke L10. Here In1.Cu is a BR_N plane
    and In2.Cu a BR_P plane joining the strips and the column to U12, D12, C103, C100 and L10's inputs.
  - Right column, x 34.5-54: the PD. The VPORT square (Q58's tab, all layers) with D10, R100 and the zener D13; U10
    with its class resistors, CGATE and C102; the POE_VDD pour from Q58's sources to C105; POE_VSS on F.Cu along the
    bottom and on both inner layers. The opto U11 sits across a 6 mm isolation band in the top-right corner, with
    the secondary (R106, the opto's outputs) in the corner itself.

Widths: 1.80 A worst case (90 W from 50 V): IPC-2221 external 10 C rise 1 oz ~0.64 mm, internal ~1.6 mm; the power
path is pours. Clearances (poe_pd.kicad_dru): POE_IN 0.6 mm (IPC-2221 Table 6-1 B2, 31-150 V) on every layer;
0.25 mm inside the LT4321/LT4294 fan-out areas and the FET courtyards; 6 mm secondary to primary.
"""
import sys

import pcbnew

ORIGIN = (100.0, 100.0)
W_PWR, W_SIG = 1.0, 0.25
VIA_BIG, VIA_SMALL = (0.8, 0.4), (0.6, 0.3)
OUTLINE = (0.0, 0.0, 54.0, 36.0)
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
    # bottom strip, bridge side of the choke: the LT4321 with its CPD (C103) and TVS (D12)
    'D12': (3.9, 32.6, 0), 'U12': (12.0, 29.6, 90), 'C103': (9.0, 24.4, 180), 'C100': (16.75, 33.6, 90),
    # the choke, then C105 (the output and the POE_VDD / POE_VSS ports); the EN zener (D13) next to the LT4321
    # (LT4321 Fig. 5), fed from VPORT by a thin trace; C101 on the choke's output
    'L10': (23.0, 29.7, 270), 'C105': (37.7, 30.4, 180), 'D13': (18.6, 23.5, 180), 'C101': (30.1, 25.0, 270),
    # PD: Q58 (tab on the VPORT square), U10 with RCLS / RCLS++ on its right, CPD (C102) and the TVS (D10) next to it
    'Q58': (41.0, 21.5, 90),
    'U10': (48.6, 16.6, 180), 'R102': (52.3, 14.9, 90), 'R101': (52.3, 18.4, 270),
    'C102': (48.9, 19.65, 0), 'R100': (44.8, 19.65, 0), 'TP41': (45.2, 15.6, 0),
    'D10': (48.2, 23.4, 0), 'R103': (52.6, 23.4, 270), 'C104': (52.8, 28.1, 270),
    'R105': (47.6, 28.4, 0), 'TP40': (48.0, 32.6, 0),
    'U11': (50.0, 6.6, 90), 'R106': (45.6, 2.0, 0),
}
for _pr, _x0, _x1, _y0, _y1, _qt, _qb, _xt, _xb, _rot in CELLS:
    _yc = (_y0 + _y1) / 2
    PLACE[_qt] = (_xt, _yc, _rot)
    PLACE[_qb] = (_xb, _yc, _rot)

# --- isolation barrier (6 mm) around the secondary corner ---------------------------------------------------
SEC = (44.0, 0.0, 54.0, 3.6)           # the secondary corner: R106 and U11's outputs
BAND = [(38.0, 0.0), (44.0, 0.0), (44.0, 3.6), (54.0, 3.6), (54.0, 9.6), (38.0, 9.6)]

# --- PD pours ---------------------------------------------------------------------------------------------------
SQ_VPORT = (34.5, 12.4, 44.5, 22.1)     # Q58's tab copper, every layer
TAB_D10 = (44.5, 20.4, 46.6, 24.4)      # VPORT on to D10's pad 1 (F.Cu)
# L10.1 (VPORT) along under the bridge to the square, F.Cu only
LEG_VPORT = [(24.4, 22.7), (34.5, 22.7), (34.5, 12.4), (36.0, 12.4), (36.0, 24.5), (28.4, 24.5), (28.4, 27.9),
             (24.4, 27.9)]
R_VDD = [(37.6, 22.7), (44.5, 22.7), (44.5, 32.0), (37.6, 32.0)]      # Q58's sources to C105.1 (F.Cu, B.Cu)
X_CMC = 23.0                            # inner planes: bridge side (BR_N / BR_P) left of this, POE_VSS right
R_VSS = [(X_CMC + 0.5, 25.1), (34.2, 25.1), (34.2, 0.5), (38.0, 0.5), (38.0, 9.6), (53.5, 9.6), (53.5, 35.5),
         (X_CMC + 0.5, 35.5)]
R_VSS_IN2 = [(X_CMC + 0.5, 22.4), (34.2, 22.4), (34.2, 0.5), (38.0, 0.5), (38.0, 9.6), (53.5, 9.6), (53.5, 35.5),
             (X_CMC + 0.5, 35.5)]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# In1: the BR_N strips, joined below the right cells (x X_CMC-X_END) to the bottom strip's BR_N plane.
# In2: the BR_P column carried on into the bottom strip's BR_P plane. The bottom-strip parts (x < X_CMC) are
# 'final' pours: while Freerouting runs, the LT4321's signals may use all four layers there.
IN1_BRN = [(X_BRNL, Y_TOP), (X_CL, Y_TOP), (X_CL, Y_BR), (X_BRNR, Y_BR), (X_BRNR, Y_TOP), (X_END, Y_TOP),
           (X_END, 24.6), (X_CMC - 0.2, 24.6), (X_CMC - 0.2, Y_BR), (X_BRNL, Y_BR)]
BOTTOM = rect(X_BRNL, Y_BR, X_CMC, 35.5)

# Pours: (net, priority, polygon, layers, stage). Stage 'route' pours exist while Freerouting runs; 'final' ones are
# added afterwards and fill around the routed signals. Overlapping pours of one net get different priorities.
ZONES = [
    (BR_N, 3, rect(X_BRNL, Y_TOP, X_CL, Y_BR), ('F.Cu', 'In2.Cu', 'B.Cu'), 'route'),
    (BR_N, 3, rect(X_BRNR, Y_TOP, X_END, Y_BR), ('F.Cu', 'In2.Cu', 'B.Cu'), 'route'),
    (BR_P, 3, rect(X_BRP, Y_TOP, X_CR, Y_BR), ('F.Cu', 'In1.Cu', 'B.Cu'), 'route'),
    (BR_N, 4, IN1_BRN, ('In1.Cu',), 'route'),
    (BR_P, 4, rect(X_BRP, Y_TOP, X_CR, Y_BR), ('In2.Cu',), 'route'),
    (BR_N, 2, BOTTOM, ('In1.Cu',), 'final'),
    (BR_P, 2, BOTTOM, ('In2.Cu',), 'final'),
    (VPORT, 3, rect(*SQ_VPORT), LAYERS, 'route'),
    (VPORT, 4, rect(*TAB_D10), ('F.Cu',), 'route'),
    (VPORT, 2, LEG_VPORT, ('F.Cu',), 'route'),
    (VDD, 3, R_VDD, ('F.Cu',), 'route'),
    (VDD, 3, R_VDD, ('B.Cu',), 'final'),
    (VSS, 1, R_VSS, ('In1.Cu',), 'route'),
    (VSS, 1, R_VSS_IN2, ('In2.Cu',), 'route'),
    (VSS, 1, R_VSS, ('F.Cu', 'B.Cu'), 'final'),
] + [(pr, 3, rect(x0, y0, x1, y1), LAYERS, 'route') for pr, x0, x1, y0, y1, *_ in CELLS]

TRACKS = []     # (net, layer, width, [points]) - points are (x, y) or ('ref', 'pad')
VIAS = []       # (net, (x, y), big)


def T(net, layer, width, *pts):
    TRACKS.append((net, layer, width, list(pts)))


def V(net, at, big=None):
    VIAS.append((net, at, big))


# ============================================================================================================
# Hand routes: every fan-out from a fine-pitch part, every gate and sense escape from the bridge, and the PD's
# short signals. Points are mm from the block corner, or ('ref', 'pad') for a pad centre. The longer signal runs
# between these vias come from Freerouting, frozen in layout_poe_pd_routes.py (see 'route' below).
# ============================================================================================================
S = lambda r, n: (r, n)
SM = False          # small via (0.6 / 0.3) on a POE_IN net: the senses and the fine-pitch fan-out

# --- bridge: gate drives and senses out of the cells ---------------------------------------------------------
# Bottom FETs, left: gate -> F.Cu stub -> via -> B.Cu down the BR_N strip -> via at the strip's foot.
T(BG('12'), 'F.Cu', W_SIG, S('Q54', '4'), (1.75, 7.7)); V(BG('12'), (1.75, 7.7))
T(BG('12'), 'B.Cu', W_SIG, (1.75, 7.7), (1.75, 23.0)); V(BG('12'), (1.75, 23.0))
T(BG('36'), 'F.Cu', W_SIG, S('Q55', '4'), (1.0, 18.4)); V(BG('36'), (1.0, 18.4))
T(BG('36'), 'B.Cu', W_SIG, (1.0, 18.4), (0.95, 18.5), (0.95, 23.8)); V(BG('36'), (0.95, 23.8))
# Bottom FETs, right: the same down the right strip, past the VPORT leg to below it.
T(BG('45'), 'F.Cu', W_SIG, S('Q56', '4'), (33.0, 4.3)); V(BG('45'), (33.0, 4.3))
T(BG('45'), 'B.Cu', W_SIG, (33.0, 4.3), (33.3, 4.6), (33.3, 25.7)); V(BG('45'), (33.3, 25.7))
T(BG('78'), 'F.Cu', W_SIG, S('Q57', '4'), (32.6, 15.1)); V(BG('78'), (32.6, 15.1))
T(BG('78'), 'B.Cu', W_SIG, (32.6, 15.1), (32.5, 15.2), (32.5, 26.5)); V(BG('78'), (32.5, 26.5))
# Top FETs: gate -> via in the cell -> In1 down the cell / BR_P gap -> via below the bridge.
T(TG('12'), 'F.Cu', W_SIG, S('Q50', '4'), (12.67, 8.15)); V(TG('12'), (12.67, 8.15))
T(TG('12'), 'In1.Cu', W_SIG, (12.67, 8.15), (13.35, 8.85), (13.35, 22.9), (13.5, 23.6)); V(TG('12'), (13.5, 23.6))
T(TG('36'), 'F.Cu', W_SIG, S('Q51', '4'), (12.67, 18.95)); V(TG('36'), (12.67, 18.95))
T(TG('36'), 'In1.Cu', W_SIG, (12.67, 18.95), (12.6, 19.1), (12.6, 22.8)); V(TG('36'), (12.6, 22.8))
# the right gap's exits drop below the VPORT feed to D13 (F.Cu, y 23.5)
T(TG('45'), 'F.Cu', W_SIG, S('Q52', '4'), (21.73, 3.65)); V(TG('45'), (21.73, 3.65))
T(TG('45'), 'In1.Cu', W_SIG, (21.73, 3.65), (22.3, 4.2), (22.3, 26.2)); V(TG('45'), (22.3, 26.2))
T(TG('78'), 'F.Cu', W_SIG, S('Q53', '4'), (21.73, 14.45)); V(TG('78'), (21.73, 14.45))
T(TG('78'), 'In1.Cu', W_SIG, (21.73, 14.45), (21.5, 14.7), (21.5, 25.0)); V(TG('78'), (21.5, 25.0))
# Senses: a small via in each top cell, down the gaps on In2; straight down out of each bottom cell on B.Cu.
V('PR12', (11.9, 10.2), SM)
T('PR12', 'In2.Cu', W_SIG, (11.9, 10.2), (11.9, 23.2), (11.6, 23.8)); V('PR12', (11.6, 23.8), SM)
V('PR45', (23.2, 10.2), SM)
T('PR45', 'In2.Cu', W_SIG, (23.2, 10.2), (23.2, 24.9), (23.1, 25.0)); V('PR45', (23.1, 25.0), SM)
T('PR36', 'B.Cu', W_SIG, (6.0, 21.4), (6.0, 22.9)); V('PR36', (6.0, 22.9), SM)
T('PR78', 'B.Cu', W_SIG, (24.0, 21.4), (24.0, 26.4)); V('PR78', (24.0, 26.4), SM)

# --- U12 (LT4321) fan-out: short F.Cu stubs to vias around it, inside FANOUT_U12 ----------------------------------
# top: OUTP (12) and ~EN (10) to BR_P (In2), EN (11) up the middle, OUTN (9) into the exposed pad and to BR_N (In1)
T(BR_P, 'F.Cu', 0.2, S('U12', '12'), (11.02, 27.0), (10.7, 26.0)); V(BR_P, (10.7, 26.0), SM)
T(BR_P, 'F.Cu', 0.4, (10.7, 26.0), (10.48, 25.3))                                       # to C103.1
T(EN, 'F.Cu', W_SIG, S('U12', '11'), (11.68, 24.9)); V(EN, (11.68, 24.9))
T(BR_P, 'F.Cu', 0.2, S('U12', '10'), (12.32, 27.0), (12.6, 26.0)); V(BR_P, (12.6, 26.0), SM)
T(BR_N, 'F.Cu', 0.2, S('U12', '9'), (12.98, 28.2))                                       # into the exposed pad
T(BR_N, 'F.Cu', 0.2, S('U12', '9'), (12.98, 27.0), (13.9, 26.4)); V(BR_N, (13.9, 26.4), SM)
# left: BG36, BG12 up-left; PR12, TG12 down-left
T(BG('36'), 'F.Cu', W_SIG, S('U12', '13'), (9.2, 28.62), (8.2, 27.6)); V(BG('36'), (8.2, 27.6))
T(BG('12'), 'F.Cu', W_SIG, S('U12', '14'), (8.8, 29.28), (7.6, 28.8)); V(BG('12'), (7.6, 28.8))
T('PR12', 'F.Cu', W_SIG, S('U12', '15'), (8.8, 29.92), (7.6, 30.4)); V('PR12', (7.6, 30.4), SM)
T(TG('12'), 'F.Cu', W_SIG, S('U12', '16'), (9.0, 30.57), (8.2, 31.7)); V(TG('12'), (8.2, 31.7))
# right: BG45, BG78 up-right; PR78, TG78 down-right
T(BG('45'), 'F.Cu', W_SIG, S('U12', '8'), (14.8, 28.62), (15.8, 27.6)); V(BG('45'), (15.8, 27.6))
T(BG('78'), 'F.Cu', W_SIG, S('U12', '7'), (15.2, 29.28), (16.4, 28.8)); V(BG('78'), (16.4, 28.8))
T('PR78', 'F.Cu', W_SIG, S('U12', '6'), (15.2, 29.92), (16.4, 30.4)); V('PR78', (16.4, 30.4), SM)
T(TG('78'), 'F.Cu', W_SIG, S('U12', '5'), (15.0, 30.57), (15.8, 31.7)); V(TG('78'), (15.8, 31.7))
# bottom: TG36, PR36, PR45, TG45 down
T(TG('36'), 'F.Cu', W_SIG, S('U12', '1'), (11.02, 32.4), (10.4, 33.2)); V(TG('36'), (10.4, 33.2))
T('PR36', 'F.Cu', W_SIG, S('U12', '2'), (11.68, 33.4), (11.35, 34.3)); V('PR36', (11.35, 34.3), SM)
T('PR45', 'F.Cu', W_SIG, S('U12', '3'), (12.32, 33.4), (12.65, 34.3)); V('PR45', (12.65, 34.3), SM)
T(TG('45'), 'F.Cu', W_SIG, S('U12', '4'), (12.98, 32.4), (13.6, 33.2)); V(TG('45'), (13.6, 33.2))
# The EN zener: VPORT from the leg on a thin trace (the zener only), EN pad to U12 (Freerouting)
T(VPORT, 'F.Cu', 0.4, ('D13', '1'), (24.8, 23.5))
# CPD (C103) BR_N side, the TVS (D12), C100 and the choke's inputs down to the inner planes
V(BR_N, (5.9, 25.9)); T(BR_N, 'F.Cu', 0.6, ('C103', '2'), (5.9, 25.9))
for _x in (1.0, 2.5):
    V(BR_P, (_x, 34.8)); T(BR_P, 'F.Cu', 0.8, ('D12', '1'), (_x, 34.8))
for _x in (5.3, 6.8):
    V(BR_N, (_x, 34.8)); T(BR_N, 'F.Cu', 0.8, ('D12', '2'), (_x, 34.8))
T(BR_N, 'F.Cu', 0.5, ('C100', '2'), (17.9, 32.82))                        # C100 sits beside L10.3
V(BR_P, (15.5, 35.2)); T(BR_P, 'F.Cu', 0.5, ('C100', '1'), (15.5, 35.2))
for _y in (25.7, 26.9):
    V(BR_P, (17.2, _y)); T(BR_P, 'F.Cu', 1.0, ('L10', '2'), (17.2, _y))      # L10.2 (BR_P), left of the pad
for _x in (18.6, 19.8):
    V(BR_N, (_x, 35.0))                                                     # L10.3 (BR_N), below the pad
T(BR_N, 'F.Cu', 1.0, ('L10', '3'), (19.2, 35.0)); T(BR_N, 'F.Cu', 1.0, (18.6, 35.0), (19.8, 35.0))
# C101's POE_VSS pad down to In2 (the leg is VPORT on F.Cu)
V(VSS, (31.4, 25.9)); T(VSS, 'F.Cu', 0.5, ('C101', '2'), (31.4, 25.9))

# --- PD: U10 (LT4294) fan-out and the short signals --------------------------------------------------------------
T(P_('PD_RCLSPP'), 'F.Cu', 0.2, S('U10', '4'), (51.0, 16.1), ('R102', '1'))
T(P_('PD_RCLS'), 'F.Cu', W_SIG, S('U10', '3'), (51.2, 16.6), ('R101', '1'))
T(T2P, 'F.Cu', W_SIG, S('U10', '6'), (46.3, 15.6), (46.3, 13.9), (49.9, 13.9), (50.6, 13.2), (50.6, 12.36),
  ('U11', '2'))
T(PWRGD, 'F.Cu', W_SIG, S('U10', '7'), (45.7, 16.1), ('TP41', '1'))
T(VDD, 'F.Cu', W_SIG, S('U10', '8'), (45.3, 16.6), (44.9, 17.2)); V(VDD, (44.9, 17.2), SM)
T(HSG, 'F.Cu', W_SIG, S('U10', '9'), (46.2, 17.1), (46.0, 18.2)); V(HSG, (46.0, 18.2))
T(VPIN, 'F.Cu', W_SIG, S('U10', '10'), (46.9, 17.9), (46.9, 19.0))
T(VPIN, 'F.Cu', 0.5, ('R100', '2'), ('C102', '1'))
T(VSS, 'F.Cu', 0.2, S('U10', '1'), (49.4, 17.6)); T(VSS, 'F.Cu', 0.2, S('U10', '5'), (49.4, 15.6))
T(LED, 'F.Cu', W_SIG, S('U11', '1'), (48.73, 12.95)); V(LED, (48.73, 12.95))
T(HSG, 'F.Cu', W_SIG, S('Q58', '4'), (42.0, 24.15)); V(HSG, (42.0, 24.15))
T(CG, 'F.Cu', W_SIG, ('R103', '2'), ('C104', '1'))
# the secondary corner
T('POE_T2P_N', 'F.Cu', W_SIG, ('R106', '2'), ('U11', '4'))



# Nets Freerouting connects (between the vias above and the pads left open); everything else is a pour.
ROUTED = {BG('12'), BG('36'), BG('45'), BG('78'), TG('12'), TG('36'), TG('45'), TG('78'), 'PR12', 'PR36', 'PR45',
          'PR78', EN, HSG, VDD, LED}
# While Freerouting runs it gets keep-outs over every power pour it must not cross (it doesn't treat other nets'
# pours as obstacles): (polygon, layers)
KEEP_ROUTE = [
    (rect(0.0, 0.0, X_END + 0.3, Y_BR + 0.25), LAYERS),                    # the bridge: cells, strips, BR_P column
    (rect(X_CMC - 0.2, Y_BR, 54.0, 36.0), ('In1.Cu', 'In2.Cu')),           # the PD side's inner planes
    (rect(*SQ_VPORT), ('F.Cu', 'B.Cu')),                                    # Q58's square
    (rect(*TAB_D10), ('F.Cu',)),
    (LEG_VPORT, ('F.Cu',)),
    (R_VDD, ('F.Cu',)),
    (rect(X_CMC + 0.5, 32.2, 53.5, 35.5), ('F.Cu',)),                      # the POE_VSS return along the bottom
]
# For these nets Freerouting only joins the listed pins to the hand-made wiring (the cells and pours do the rest).
ROUTE_PINS = {'PR12': [('U12', '15')], 'PR36': [('U12', '2')], 'PR45': [('U12', '3')], 'PR78': [('U12', '6')],
              VDD: [('U10', '8'), ('R105', '1'), ('C105', '1')]}

# Stitching and thermal vias, 0.8 / 0.4 mm on a grid, kept clear of every pad, track and via of another net
# (stitch() below): (net, rectangle, pitch)
STITCH = [(pr, (x0 + 0.9, y0 + 0.9, x1 - 0.9, y1 - 0.9), 2.5) for pr, x0, x1, y0, y1, *_ in CELLS] + [
    (BR_P, (X_BRP + 0.9, Y_TOP + 0.9, X_CR - 0.9, Y_BR - 0.9), 2.5),
    (BR_N, (X_BRNL + 0.8, Y_TOP + 0.8, X_CL - 0.8, Y_BR - 0.8), 2.5),
    (BR_N, (X_BRNR + 0.8, Y_TOP + 0.8, X_END - 0.8, Y_BR - 0.8), 2.5),
    (VPORT, (SQ_VPORT[0] + 0.9, SQ_VPORT[1] + 0.9, SQ_VPORT[2] - 0.9, SQ_VPORT[3] - 0.9), 2.5),
    (VDD, (38.4, 23.6, 43.8, 31.4), 2.5),
    (VSS, (24.5, 31.6, 53.0, 35.0), 3.0),
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


def pours(board, stages):
    for name, prio, pts, layers, stage in ZONES:
        if stage not in stages:
            continue
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


def routes_file():
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layout_poe_pd_routes.py')


def frozen_routes():
    """The Freerouting result, frozen: (tracks, vias) as plain data, or ([], []) before the first 'route'."""
    import os
    path = routes_file()
    if not os.path.exists(path):
        return [], []
    ns = {}
    exec(open(path, encoding='utf-8').read(), ns)
    return ns['TRACKS'], ns['VIAS']


def build(path, stages, with_frozen):
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
    n_frozen = 0
    if with_frozen:
        ftracks, fvias = frozen_routes()
        for name, layer, width, pts in ftracks:
            track(board, name, layer, width, pts)
        for name, p, d, h in fvias:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(P(*p))
            v.SetWidth(pcbnew.FromMM(d))
            v.SetDrill(pcbnew.FromMM(h))
            v.SetNet(net(board, name))
            v.SetLocked(True)
            board.Add(v)
        n_frozen = len(ftracks) + len(fvias)
    rule_area(board, 'isolation barrier 6 mm', BAND, True)
    if 'final' not in stages:
        for k, (pts, layers) in enumerate(KEEP_ROUTE):
            rule_area(board, f'route keep-out {k}', pts, True, layers)
    if 'final' in stages:       # Freerouting reads rule areas as keep-outs, so these only go on the finished board
        ux, uy = PLACE['U12'][:2]
        rule_area(board, 'FANOUT_U12', rect(ux - 4.8, uy - 4.8, ux + 4.8, uy + 4.8), False)
        ux, uy = PLACE['U10'][:2]
        rule_area(board, 'FANOUT_U10', rect(ux - 3.6, uy - 3.6, ux + 3.6, uy + 3.6), False)
    n_stitch = stitch(board) if 'final' in stages else 0
    pours(board, stages)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'{path}: {len(PLACE)} parts placed and locked, {len(TRACKS)} hand track runs, {len(VIAS)} hand vias, '
          f'{n_frozen} Freerouting items, {n_stitch} stitching vias, pours {"+".join(stages)}; zones filled')


def prepare(path):
    build(path, ('route', 'final'), True)


def route(path):
    """Once, to make layout_poe_pd_routes.py: the hand routes and the 'route' pours, then Freerouting joins the
    ROUTED nets on F.Cu and B.Cu (In1 / In2 are planes), and its new tracks and vias are written out as data."""
    import os
    import re
    import subprocess
    build(path, ('route',), False)
    board = pcbnew.LoadBoard(path)
    dsn = path[:-10] + '.dsn'
    ses = path[:-10] + '.ses'
    pcbnew.ExportSpecctraDSN(board, dsn)
    text = open(dsn, encoding='utf-8').read()

    # keep only the ROUTED nets in the network (and only ROUTE_PINS pins where listed)
    def keep(m):
        name = m.group(1).strip('"')
        if name not in ROUTED:
            return ''
        if name in ROUTE_PINS:
            pins = ' '.join(f'{r}-{n}' for r, n in ROUTE_PINS[name])
            return f'(net {m.group(1)}\n      (pins {pins})\n    )'
        return m.group(0)
    text = re.sub(r'\(net ("[^"]*"|\S+)\s*\n\s*\(pins[^)]*\)\s*\)', keep, text)
    text = text.replace('(clearance 150)', '(clearance 350)')      # signals 0.35 mm apart (DRC needs 0.15)
    # POE_IN keeps its 0.6 mm (the .kicad_dru rule; the fine-pitch exceptions are all hand-routed); the senses are
    # 0.25 mm traces with small vias, like every other signal
    text = re.sub(r'(\(class POE_IN[^(]*\(circuit\s*)\(use_via "Via\[0-3\]_800:400_um"\)\s*\(width 500\)',
                  r'\1(use_via "Via[0-3]_600:300_um")\n        (width 250)', text)
    open(dsn, 'w', encoding='utf-8').write(text)
    java = r'C:\Program Files\Eclipse Adoptium\jre-25.0.5.8-hotspot\bin\java.exe'
    jar = os.path.join(os.path.expanduser('~'), '.kicad-mcp', 'freerouting.jar')
    subprocess.run([java, '-jar', jar, '-de', dsn, '-do', ses, '-mp', '30', '-mt', '1'], check=True)
    before = {(t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
              for t in board.GetTracks()}
    pcbnew.ImportSpecctraSES(board, ses)
    mm = pcbnew.ToMM
    tracks, vias = [], []
    for t in board.GetTracks():
        key = (t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
        if key in before or t.GetNetname() not in ROUTED:      # power nets are pours, whatever Freerouting drew
            continue
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition()
            vias.append((t.GetNetname(), (round(mm(q.x) - ORIGIN[0], 4), round(mm(q.y) - ORIGIN[1], 4)),
                         round(mm(t.GetWidth(pcbnew.F_Cu)), 3), round(mm(t.GetDrill()), 3)))
        else:
            a, b = t.GetStart(), t.GetEnd()
            tracks.append((t.GetNetname(), board.GetLayerName(t.GetLayer()), round(mm(t.GetWidth()), 3),
                           [(round(mm(a.x) - ORIGIN[0], 4), round(mm(a.y) - ORIGIN[1], 4)),
                            (round(mm(b.x) - ORIGIN[0], 4), round(mm(b.y) - ORIGIN[1], 4))]))
    with open(routes_file(), 'w', encoding='utf-8', newline='\n') as f:
        f.write('"""Signal runs between the hand-made fan-out vias of layout_poe_pd.py, routed once by Freerouting 2.5.0\n'
                'on F.Cu and B.Cu and frozen here as data (layout_poe_pd.py route writes this file; prepare reads it).\n'
                '(net, layer, width mm, [(x, y), (x, y)]) and (net, (x, y), via diameter, drill), mm from the block corner.\n'
                '"""\n')
        f.write('TRACKS = [\n' + ''.join(f'    {t!r},\n' for t in tracks) + ']\n')
        f.write('VIAS = [\n' + ''.join(f'    {v!r},\n' for v in vias) + ']\n')
    print(f'routed: {len(tracks)} track segments, {len(vias)} vias -> {routes_file()}')




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
    modes = {'prepare': prepare, 'finish': finish, 'copper': copper, 'route': route}
    if len(sys.argv) != 3 or sys.argv[1] not in modes:
        raise SystemExit(__doc__)
    modes[sys.argv[1]](sys.argv[2])
