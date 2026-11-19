"""layout_poe_pd.py: the poe_pd block's PCB layout (LT4294 + LT4321), made headless with KiCad 10's pcbnew Python.

    "<KiCad>\\bin\\python.exe" layout_poe_pd.py prepare <poe_pd.kicad_pcb>   everything below, then zones filled
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py finish  <poe_pd.kicad_pcb>   refill zones only

Nothing is autorouted: every part, track, via and pour is placed by this script (BLOCK.md section 9).

Arrangement (mm from the block's top-left corner, placed at ORIGIN):
  - The ideal-diode bridge is four horizontal pair rows (12, 36 | gap | 45, 78), each a PR pour of
    43.8 x 12 mm on F.Cu and B.Cu. A BR_P strip runs down the left (with a band along the top to L10) and a
    BR_N strip down the right. Each row's top FET (PSMN075, tab = drain = BR_P) sits on the left edge with
    its tab in the BR_P strip and its sources in the row; each row's bottom FET sits on the right edge with
    its tab in the row and its sources in the BR_N strip. In the one-pair-set worst case one top FET and one
    bottom FET conduct; each has a ~525 mm2 pour (the row, or the strip), both layers, via-stitched.
  - The LT4321 sits in the gap between the two pair sets. Its gate drives and pair senses fan out on F.Cu to
    vias and run on B.Cu (TG lines down the left, BG lines down the right), so the F.Cu pours stay whole.
  - L10 (choke) at the top right of the bridge, then the PD section: VPORT band (top), VSS pour, POE_VDD pour,
    the LT4294 with its hot-swap FET, class resistors, CGATE, the output cap C105, the T2P opto, the 6 mm
    isolation barrier and the secondary pads on the right edge.

Copper sizing (calc/poe_pd_90w.py and BLOCK.md section 9): each conducting bridge FET loses 0.62 W at the 50 V,
175 C Rds(on) worst case. Nexperia AN90003 Rev 5.0 Fig. 25 (LFPAK33, one 2 oz layer, still air) gives Tj
~68 C at 0.5 W with a 20 x 20 mm pour (~96 K/W); our pours are >= 525 mm2 on each of two 1 oz layers,
stitched, taken as equal to that single 2 oz layer. Tj ~ 50 + 0.62 x 96 = 110 C at 50 C air, under
the 120 C PCB limit and the 125 C design limit.

Widths: 1.73 A, IPC-2221 external 10 C rise 1 oz ~0.64 mm: the power path is pours, the short power stubs 1.0 mm.
Clearances (poe_pd.kicad_dru): POE_IN 0.6 mm (IPC-2221 Table 6-1 B2, 31-150 V); 0.25 mm inside the LT4321 and
LT4294 fan-out areas and the FET courtyards (functional insulation inside the primary, at the parts' own pin
pitch); 6 mm secondary to primary.
"""
import sys

import pcbnew

ORIGIN = (100.0, 100.0)
W_PWR, W_SIG, W_SENSE = 1.0, 0.25, 0.25
VIA_BIG, VIA_SMALL = (0.8, 0.4), (0.6, 0.3)

BR_P, BR_N = '/PoE PD/BR_P', '/PoE PD/BR_N'
VPORT, VPIN = '/PoE PD/PD_VPORT', '/PoE PD/PD_VPIN'
VSS, VDD, PWRGD = 'POE_VSS', 'POE_VDD', 'PD_PWRGD'
PRS = ('PR12', 'PR36', 'PR45', 'PR78')
P_ = lambda n: '/PoE PD/' + n
POE_IN = {VDD, VSS, BR_P, BR_N, VPORT, VPIN} | set(PRS)

# rows: (pair, y0, y1, top FET, bottom FET)
ROWS = [('PR12', 0.0, 12.0, 'Q50', 'Q54'), ('PR36', 13.0, 25.0, 'Q51', 'Q55'),
        ('PR45', 38.0, 50.0, 'Q52', 'Q56'), ('PR78', 51.0, 63.0, 'Q53', 'Q57')]
PR_X = (11.3, 55.1)
XT, XB = 10.4, 54.6          # top / bottom FET centres (both at 180 degrees: tab left, sources right)

PLACE = {
    'U12': (33.0, 31.5, 0), 'C103': (37.8, 34.6, 270),
    'D12': (62.8, 2.3, 270), 'C100': (59.5, -1.1, 270), 'L10': (72.0, 6.0, 270),
    'D10': (79.8, 5.6, 270), 'C101': (84.0, 5.0, 270), 'D13': (86.5, 1.0, 0),
    'R100': (96.0, 12.0, 270), 'C102': (94.5, 16.0, 180),
    'Q58': (104.0, 3.6, 90), 'R103': (100.0, 8.0, 180), 'C104': (99.18, 11.2, 270),
    'U10': (98.0, 20.0, 0), 'R101': (93.5, 20.0, 180), 'R102': (93.5, 22.4, 180),
    'TP41': (103.2, 19.9, 0), 'TP40': (85.0, 30.0, 0), 'C105': (106.0, 31.0, 270),
    'R105': (110.0, 18.0, 0), 'U11': (118.0, 22.0, 0), 'R106': (125.0, 18.0, 270),
}
for pr, y0, y1, qt, qb in ROWS:
    PLACE[qt] = (XT, (y0 + y1) / 2, 180)
    PLACE[qb] = (XB, (y0 + y1) / 2, 180)
OUTLINE = (-2.0, -9.0, 128.0, 65.0)
BARRIER_X = (114.8, 120.8)

# Pours: (net, priority, polygon); each is drawn on F.Cu and B.Cu.
ZONES = [
    (BR_P, 2, [(0, -7.0), (70.0, -7.0), (70.0, 4.3), (66.4, 4.3), (66.4, -1.4), (10.0, -1.4), (10.0, 63.0),
               (0, 63.0)]),
    (BR_N, 2, [(55.6, -0.8), (65.0, -0.8), (65.0, 7.6), (69.8, 7.6), (69.8, 12.0), (65.0, 12.0), (65.0, 63.0),
               (55.6, 63.0)]),
    (VPORT, 2, [(74.4, -7.0), (106.0, -7.0), (106.0, 4.4), (74.4, 4.4)]),
    (VDD, 2, [(99.6, 5.0), (112.0, 5.0), (112.0, 27.5), (99.6, 27.5)]),
    (VSS, 1, [(74.4, 5.0), (112.0, 5.0), (112.0, 63.0), (74.4, 63.0)]),
] + [(pr, 2, [(PR_X[0], y0), (PR_X[1], y0), (PR_X[1], y1), (PR_X[0], y1)]) for pr, y0, y1, _, _ in ROWS]

# Locked tracks: (net, layer, width, points)
TRACKS = []
VIAS = []


def T(net, layer, width, *pts):
    TRACKS.append((net, layer, width, list(pts)))


def V(net, at, big=None):
    VIAS.append((net, at, big))


# --- bridge FET stubs: gates to vias (F.Cu), the via on B.Cu carries the drive --------------------------
for pr, y0, y1, qt, qb in ROWS:
    yc = (y0 + y1) / 2
    # top FET gate pad at (XT + 1.53, yc - 0.97); via above it inside the row pour
    T(P_('PD_TG' + pr[2:]), 'F.Cu', W_SIG, (XT + 1.53, yc - 0.97), (12.6, yc - 1.6), (12.6, yc - 2.4))
    V(P_('PD_TG' + pr[2:]), (12.6, yc - 2.4))
    # bottom FET gate pad at (XB + 1.53, yc - 0.97); via above it inside the BR_N strip
    T(P_('PD_BG' + pr[2:]), 'F.Cu', W_SIG, (XB + 1.53, yc - 0.97), (56.6, yc - 1.6), (56.6, yc - 2.4))
    V(P_('PD_BG' + pr[2:]), (56.6, yc - 2.4))
    # tab and source stubs make sure the pours reach the FET pads (the top FET's sources sit in the row pour)
    T(BR_P, 'F.Cu', W_PWR, (XT - 0.41, yc), (8.6, yc))
    T(pr, 'F.Cu', 0.4, (XT + 1.53, yc + 0.33), (13.4, yc + 0.33))
    T(pr, 'F.Cu', W_PWR, (XB - 0.41, yc), (52.8, yc))
    T(BR_N, 'F.Cu', W_PWR, (XB + 1.53, yc + 0.33), (57.4, yc + 0.33), (57.4, yc + 1.4))

# --- LT4321 (U12 at 33.0, 31.5) fan-out -------------------------------------------------------------------
TG = lambda p: P_('PD_TG' + p)
BG = lambda p: P_('PD_BG' + p)
# top side pins (y 29.66): 16 TG12 (32.03), 15 PR12 (32.67), 14 BG12 (33.33), 13 BG36 (33.97)
T(TG('12'), 'F.Cu', W_SIG, (32.03, 29.3), (32.03, 28.9), (30.4, 27.4)); V(TG('12'), (30.4, 27.4))
T(TG('12'), 'B.Cu', W_SIG, (30.4, 27.4), (14.0, 27.4), (14.0, 3.6), (12.6, 3.6))
T('PR12', 'F.Cu', W_SENSE, (32.67, 29.3), (32.67, 27.0)); V('PR12', (32.67, 27.0))
T('PR12', 'B.Cu', W_SENSE, (32.67, 27.0), (32.67, 6.0)); V('PR12', (32.67, 6.0))
T(BG('12'), 'F.Cu', W_SIG, (33.33, 29.3), (33.33, 28.9), (34.6, 27.6)); V(BG('12'), (34.6, 27.6))
T(BG('12'), 'B.Cu', W_SIG, (34.6, 27.6), (34.6, 26.2), (53.2, 26.2), (53.2, 3.6), (56.6, 3.6))
T(BG('36'), 'F.Cu', W_SIG, (33.97, 29.3), (33.97, 29.0), (36.0, 27.6)); V(BG('36'), (36.0, 27.6))
T(BG('36'), 'B.Cu', W_SIG, (36.0, 27.6), (54.4, 27.6), (54.4, 16.6), (56.6, 16.6))
# left side pins (x 31.16): 1 TG36 (30.53), 2 PR36 (31.17), 3 PR45 (31.83), 4 TG45 (32.47)
T(TG('36'), 'F.Cu', W_SIG, (30.8, 30.53), (30.33, 30.53), (29.4, 29.6), (29.4, 29.2)); V(TG('36'), (29.4, 29.2))
T(TG('36'), 'B.Cu', W_SIG, (29.4, 29.2), (13.2, 29.2), (13.2, 16.6), (12.6, 16.6))
T('PR36', 'F.Cu', W_SENSE, (30.8, 31.17), (28.0, 31.17), (28.0, 24.4))
T('PR45', 'F.Cu', W_SENSE, (30.8, 31.83), (27.0, 31.83), (27.0, 38.6))
T(TG('45'), 'F.Cu', W_SIG, (30.8, 32.47), (30.33, 32.47), (29.4, 33.4), (29.4, 34.0)); V(TG('45'), (29.4, 34.0))
T(TG('45'), 'B.Cu', W_SIG, (29.4, 34.0), (13.2, 34.0), (13.2, 41.6), (12.6, 41.6))
# bottom side pins (y 33.34): 5 TG78 (32.03), 6 PR78 (32.67), 7 BG78 (33.33), 8 BG45 (33.97)
T(TG('78'), 'F.Cu', W_SIG, (32.03, 33.7), (32.03, 34.1), (30.6, 35.5), (30.6, 35.6)); V(TG('78'), (30.6, 35.6))
T(TG('78'), 'B.Cu', W_SIG, (30.6, 35.6), (14.0, 35.6), (14.0, 54.6), (12.6, 54.6))
T('PR78', 'F.Cu', W_SENSE, (32.67, 33.7), (32.67, 36.0)); V('PR78', (32.67, 36.0))
T('PR78', 'B.Cu', W_SENSE, (32.67, 36.0), (32.67, 57.0)); V('PR78', (32.67, 57.0))
T(BG('78'), 'F.Cu', W_SIG, (33.33, 33.7), (33.33, 34.2), (34.4, 35.3), (34.4, 36.6)); V(BG('78'), (34.4, 36.6))
T(BG('78'), 'B.Cu', W_SIG, (34.4, 36.6), (34.4, 37.0), (53.2, 37.0), (53.2, 54.6), (56.6, 54.6))
T(BG('45'), 'F.Cu', W_SIG, (33.97, 33.7), (33.97, 34.0), (35.2, 35.2), (35.2, 35.9)); V(BG('45'), (35.2, 35.9))
T(BG('45'), 'B.Cu', W_SIG, (35.2, 35.9), (54.4, 35.9), (54.4, 41.6), (56.6, 41.6))
# right side pins (x 34.84): 12 OUTP (30.53), 11 EN (31.17), 10 ~EN (31.83), 9 OUTN (32.47)
T(BR_N, 'F.Cu', 0.15, (34.5, 32.35), (33.9, 32.35))                         # pin 9 into the exposed pad
T(BR_N, 'F.Cu', 0.3, (35.2, 32.47), (35.4, 32.47), (36.3, 33.4), (36.3, 35.4), (37.0, 36.08), (37.8, 36.08))
T(BR_N, 'F.Cu', 0.5, (37.8, 36.6), (55.8, 36.6))                             # C103.2 -> BR_N strip
# OUTP (12) and ~EN (10) each drop to B.Cu, meet, and come up on the F.Cu BR_P riser at x 40, which runs from
# C103.1 to the BR_P band (EN stays between them on its own pin).
T(BR_P, 'F.Cu', W_SIG, (35.2, 30.53), (35.37, 30.53), (35.9, 30.0), (36.3, 29.5)); V(BR_P, (36.3, 29.5), False)
T(BR_P, 'F.Cu', 0.2, (35.2, 31.83), (36.05, 31.83)); V(BR_P, (36.05, 31.83), False)
T(BR_P, 'B.Cu', W_SIG, (36.3, 29.5), (40.0, 29.5)); V(BR_P, (40.0, 29.5), False)
T(BR_P, 'B.Cu', W_SIG, (36.05, 31.83), (37.2, 31.83), (37.2, 29.5))
T(BR_P, 'F.Cu', 0.4, (37.8, 33.12), (40.0, 33.12), (40.0, -1.6))
T(P_('PD_BR_EN'), 'F.Cu', 0.2, (35.2, 31.17), (38.5, 31.17)); V(P_('PD_BR_EN'), (38.5, 31.17))
T(P_('PD_BR_EN'), 'B.Cu', W_SIG, (38.5, 31.17), (58.0, 31.17), (58.0, 1.0), (89.4, 1.0)); V(P_('PD_BR_EN'), (89.4, 1.0))
T(P_('PD_BR_EN'), 'F.Cu', W_SIG, (89.4, 1.0), (88.15, 1.0))

# --- bridge outputs to the choke ---------------------------------------------------------------------------
T(BR_P, 'F.Cu', W_PWR, (62.8, 0.15), (62.8, -1.6))          # D12 cathode up to the BR_P band
T(BR_P, 'F.Cu', 0.5, (59.5, -1.88), (59.5, -2.6))           # C100.1
T(BR_N, 'F.Cu', 0.5, (59.5, -0.32), (59.5, 0.4))            # C100.2

# --- PD section ---------------------------------------------------------------------------------------------
T(VPORT, 'F.Cu', W_PWR, (75.8, 2.9), (76.4, 2.9))
T(VSS, 'F.Cu', W_PWR, (75.8, 9.1), (76.4, 9.1))
T(VPORT, 'F.Cu', 0.5, (96.0, 4.0), (96.0, 11.09))           # VPORT down to R100 through the VSS pour
T(VPIN, 'F.Cu', 0.4, (96.0, 12.91), (96.0, 16.0))
T(VPIN, 'F.Cu', 0.2, (99.6, 19.0), (100.5, 19.0), (100.5, 16.0), (95.98, 16.0))
T(P_('PD_HSGATE'), 'F.Cu', 0.2, (99.6, 19.5), (101.5, 19.5), (101.5, 8.0), (104.97, 8.0), (104.97, 5.4))
T(P_('PD_HSGATE'), 'F.Cu', W_SIG, (101.5, 8.0), (100.82, 8.0))
T(P_('PD_CGATE'), 'F.Cu', W_SIG, (99.18, 8.0), (99.18, 9.72))
T(VDD, 'F.Cu', 0.2, (99.6, 20.0), (100.6, 20.0))
T(PWRGD, 'F.Cu', 0.2, (99.6, 20.5), (102.4, 20.5), (103.2, 19.9))
T(P_('PD_T2P'), 'F.Cu', 0.2, (99.6, 21.0), (111.5, 21.0), (111.5, 23.27), (112.4, 23.27))
T(P_('PD_RCLS'), 'F.Cu', W_SIG, (94.41, 20.0), (96.4, 20.0))
T(P_('PD_RCLSPP'), 'F.Cu', W_SIG, (94.41, 22.4), (95.5, 22.4), (95.7, 20.5), (96.4, 20.5))
T(P_('T2P_LED_A'), 'F.Cu', W_SIG, (111.46, 18.0), (112.6, 19.2), (112.6, 20.73), (113.24, 20.73))
T('POE_T2P_N', 'F.Cu', W_SIG, (125.0, 18.82), (125.0, 19.6), (123.4, 20.73), (122.76, 20.73))

# --- stitching / thermal vias ------------------------------------------------------------------------------
for pr, y0, y1, qt, qb in ROWS:
    yc = (y0 + y1) / 2
    for x in [16.0 + 3.0 * k for k in range(12)]:
        if 31.2 < x < 34.2 or 38.5 < x < 41.5:     # the PR12/PR78 sense lines (B.Cu) and the BR_P riser (F.Cu)
            continue
        for y in (yc - 3.5, yc + 3.5):
            V(pr, (x, y), True)
    for y in (yc - 1.6, yc + 1.6):
        V(pr, (51.6, y), True)                               # beside the bottom FET's tab
        V(BR_P, (7.4, y), True)                              # beside the top FET's tab
for y in [-5.0 + 3.0 * k for k in range(23)]:
    V(BR_P, (2.5, y), True)
    if y < -2.0:
        for x in [16.0 + 4.0 * k for k in range(13)]:
            V(BR_P, (x, -4.5), True)
for y in [8.0 + 3.0 * k for k in range(19)]:
    for x in (60.0, 63.0):
        V(BR_N, (x, y), True)
for x in (78.0, 82.0, 90.0, 94.0):
    V(VPORT, (x, -4.5), True)
for x, y in ((80.0, 10.0), (84.0, 10.0), (88.0, 10.0), (80.0, 14.0), (84.0, 14.0), (88.0, 14.0),
             (80.0, 26.0), (84.0, 26.0), (90.0, 26.0), (80.0, 40.0), (90.0, 40.0), (100.0, 44.0), (110.0, 44.0)):
    V(VSS, (x, y), True)
for x, y in ((107.0, 8.0), (110.0, 8.0), (107.0, 12.0), (110.0, 12.0), (104.0, 23.0),
             (100.6, 6.2), (102.6, 6.2)):                   # Q58's sources: their F.Cu island goes down here
    V(VDD, (x, y), True)


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


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
    missing = {fp.GetReference() for fp in board.GetFootprints()} - set(PLACE)
    if missing:
        raise SystemExit('no position for: ' + ' '.join(sorted(missing)))


def check_pads(board):
    """The hand-written routes assume these pad positions: stop if a rotation or footprint changed."""
    expect = {('U12', '1'): (31.16, 30.53), ('U12', '8'): (33.97, 33.34), ('U12', '12'): (34.84, 30.53),
              ('U12', '15'): (32.67, 29.66), ('U10', '10'): (99.45, 19.0), ('U10', '3'): (96.55, 20.0),
              ('Q50', '4'): (XT + 1.53, 5.03), ('Q54', '4'): (XB + 1.53, 5.03), ('Q58', '4'): (104.97, 5.13),
              ('L10', '2'): (68.2, 2.9), ('L10', '1'): (75.8, 2.9), ('U11', '2'): (113.24, 23.27),
              ('C103', '1'): (37.8, 33.12), ('R100', '1'): (96.0, 11.09)}
    bad = []
    for (ref, num), (x, y) in expect.items():
        p = board.FindFootprintByReference(ref).FindPadByNumber(num).GetPosition()
        px, py = pcbnew.ToMM(p.x) - ORIGIN[0], pcbnew.ToMM(p.y) - ORIGIN[1]
        if abs(px - x) > 0.05 or abs(py - y) > 0.05:
            bad.append(f'{ref}.{num} at ({px:.2f}, {py:.2f}), expected ({x}, {y})')
    if bad:
        raise SystemExit('pad positions moved:\n  ' + '\n  '.join(bad))


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
        spots = []
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


def via(board, name, at, big=None):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(*at))
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


def rule_area(board, name, pts, keepout):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(keepout)
    z.SetDoNotAllowVias(keepout)
    z.SetDoNotAllowZoneFills(keepout)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    z.Outline().AddOutline(polygon(pts))
    z.SetLocked(True)
    board.Add(z)


def pours(board):
    for name, prio, pts in ZONES:
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            z = pcbnew.ZONE(board)
            z.SetLayer(layer)
            z.SetNet(net(board, name))
            z.SetAssignedPriority(prio)
            z.SetMinThickness(pcbnew.FromMM(0.25))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetZoneName(f'{name.split("/")[-1]} pour')
            z.Outline().AddOutline(polygon(pts))
            z.SetLocked(True)
            board.Add(z)


def prepare(path):
    board = pcbnew.LoadBoard(path)
    clear(board)
    place(board)
    check_pads(board)
    outline(board)
    hidden = place_refs(board)
    if hidden:
        print('designators with no clear spot (hidden on silk, kept on F.Fab):', ' '.join(hidden))
    for name, layer, width, pts in TRACKS:
        track(board, name, layer, width, pts)
    for name, at, big in VIAS:
        via(board, name, at, big)
    x0, y0, x1, y1 = OUTLINE
    rule_area(board, 'isolation barrier 6 mm', [(BARRIER_X[0], y0), (BARRIER_X[1], y0), (BARRIER_X[1], y1),
                                                (BARRIER_X[0], y1)], True)
    rule_area(board, 'FANOUT_U12', [(28.0, 26.5), (38.0, 26.5), (38.0, 36.5), (28.0, 36.5)], False)
    rule_area(board, 'FANOUT_U10', [(93.8, 16.0), (102.2, 16.0), (102.2, 24.0), (93.8, 24.0)], False)
    pours(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'prepared {path}: {len(PLACE)} parts placed and locked, {len(TRACKS)} track runs, {len(VIAS)} vias, '
          f'{len(ZONES)} pours on F.Cu and B.Cu, barrier and fan-out areas; zones filled')


def finish(path):
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'zones filled: {path}')


if __name__ == '__main__':
    modes = {'prepare': prepare, 'finish': finish}
    if len(sys.argv) != 3 or sys.argv[1] not in modes:
        raise SystemExit(__doc__)
    modes[sys.argv[1]](sys.argv[2])
