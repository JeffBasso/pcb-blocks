"""layout_poe_pd.py: the poe_pd block's PCB layout, made headless with KiCad 10's pcbnew Python (pcb-blocks#2).

    "<KiCad>\\bin\\python.exe" layout_poe_pd.py prepare <poe_pd.kicad_pcb>   placement, power copper, barrier
    "<KiCad>\\bin\\python.exe" layout_poe_pd.py finish  <poe_pd.kicad_pcb>   fill zones after Freerouting

`prepare` clears the board's copper and drawings, then places and locks all 31 parts and draws, locked:
  - the bridge: BR_P / BR_N buses and the four PR links (1.0 mm F.Cu);
  - the VDD and VSS rails from L10 past D10, C102, C101 to U10 (1.0 mm), and VDD to C105 over B.Cu (1.0 mm);
  - U10's fan-out (0.25-0.3 mm stubs, kept inside the courtyard where pins are 0.65 mm apart);
  - PRI_RTN from U10 pins 10-12 to C105 and the C103/C104 returns (1.0 mm);
  - a POE_VSS pour on B.Cu under U10 / D10 / the class resistors (thermal pad and VSS return), with vias;
  - the isolation barrier: a 6 mm keep-out band (no tracks, vias or pours on any layer) under U11/U12;
  - the test project's outline (Edge.Cuts; not part of the design block copy).
Every other connection (small signals: DEN, CLSA, CLSB, REF, PG, TPH/TPL, LED drive, VCIN/VCOUT, CONV_SS and
the secondary side) is left for Freerouting (see BLOCK.md section 9).

Widths: the PD current at Class 8 is ~1.7 A (71 W from 42 V); IPC-2221 external, 10 C rise, 1 oz gives
~0.62 mm, so the power path is 1.0 mm. Clearances: POE_IN nets 0.6 mm (IPC-2221 Table 6-1 B2, 31-150 V),
0.2 mm inside U10's courtyard (B4 under the part body) - the same rules as wallnode-amp (poe_pd.kicad_dru).
Barrier: 6 mm, wallnode-amp's moat placeholder until IEC 62368-1 is in the library; the FOD817 pads are
7.52 mm apart.
Coordinates are mm from the block's top-left corner (0, 0), placed at ORIGIN on the sheet.
"""
import sys

import pcbnew

ORIGIN = (100.0, 100.0)
W_PWR, W_NECK, W_SIG = 1.0, 0.3, 0.25

# ref: (x, y, rotation) - see the module docstring for the arrangement.
PLACE = {
    # secondary strip (top): pull-ups; the opto outputs face up
    'R107': (41.2, 1.6, 0), 'R108': (49.2, 1.6, 0),
    'U11': (43.0, 9.5, 90), 'U12': (51.0, 9.5, 90),
    # primary: LED drive under the optos
    'R105': (41.73, 18.0, 90), 'R106': (49.73, 18.0, 90),
    # bridges: one row per pair set, high diode left, low diode right; PR joins them in the middle
    'D50': (6.0, 16.0, 0), 'D54': (15.0, 16.0, 0),
    'D51': (6.0, 21.9, 0), 'D55': (15.0, 21.9, 0),
    'D52': (6.0, 27.8, 0), 'D56': (15.0, 27.8, 0),
    'D53': (6.0, 33.7, 0), 'D57': (15.0, 33.7, 0),
    'C100': (19.9, 24.1, 270),
    'L10': (27.0, 24.1, 270),
    # across the VDD (y 21) and VSS (y 27.2) rails
    'D10': (34.9, 24.1, 270), 'C102': (38.3, 24.1, 270), 'C101': (40.4, 24.1, 270),
    'TP40': (34.9, 30.0, 0),
    'U10': (47.0, 24.1, 0),
    'R100': (44.4, 19.4, 0),
    'R101': (41.6, 30.6, 270), 'R102': (45.7, 29.6, 270), 'R103': (48.0, 29.6, 270),   # signal pad 1 on top
    'R104': (54.6, 24.1, 0), 'TP41': (55.6, 22.0, 0),
    'C103': (53.2, 28.4, 90), 'C104': (54.8, 28.4, 90), 'D11': (54.0, 31.6, 180),
    # bulk VDD-RTN (PMP20878 C28) under U10: RTN comes round on F.Cu, VDD under the VSS pour on B.Cu;
    # its pads are the block's POE_VDD and PRI_RTN outputs to the converter
    'C105': (40.0, 38.5, 0),
}
OUTLINE = (-2.5, -0.5, 59.5, 44.5)
BARRIER = (6.5, 12.5)          # y band of the keep-out, full width

ROWS = (16.0, 21.9, 27.8, 33.7)
BR_P, BR_N, VSS = '/PoE PD/BR_P', '/PoE PD/BR_N', '/PoE PD/POE_VSS'
PRS = ('PR12', 'PR36', 'PR45', 'PR78')

# Locked copper: (net, layer, width, [points])
TRACKS = [
    # bridge buses and the BR_P run over the top of the bridge to L10 pin 2; BR_N straight to pin 3
    (BR_P, 'F.Cu', W_PWR, [(4.88, 33.7), (4.88, 13.2), (23.2, 13.2), (23.2, 21.0)]),
    (BR_N, 'F.Cu', W_PWR, [(17.86, 16.0), (17.86, 33.7)]),
    (BR_N, 'F.Cu', W_PWR, [(17.86, 27.2), (23.2, 27.2)]),
] + [
    (pr, 'F.Cu', W_PWR, [(8.86, y), (13.88, y)]) for pr, y in zip(PRS, ROWS)
] + [
    # C100 across the bridge outputs
    (BR_P, 'F.Cu', 0.5, [(19.9, 23.32), (19.9, 22.4), (22.4, 21.5)]),
    (BR_N, 'F.Cu', 0.5, [(19.9, 24.88), (19.9, 27.2)]),
    # VDD rail: L10 pin 1 -> D10, C102, C101 -> neck into U10 pin 1 (inside the courtyard first)
    ('POE_VDD', 'F.Cu', W_PWR, [(30.8, 21.0), (43.0, 21.0)]),
    ('POE_VDD', 'F.Cu', W_NECK, [(43.0, 21.0), (44.1, 21.6), (44.1, 22.8), (44.67, 22.8)]),
    ('POE_VDD', 'F.Cu', 0.6, [(38.3, 21.0), (38.3, 22.9)]),
    ('POE_VDD', 'F.Cu', 0.6, [(40.4, 21.0), (40.4, 23.0)]),
    ('POE_VDD', 'F.Cu', 0.4, [(43.58, 19.4), (43.58, 20.4), (43.0, 21.0)]),
    # VDD to C105 pad 1: down the left of the VSS pour on B.Cu, then a short F.Cu stub into the pad
    ('POE_VDD', 'B.Cu', W_PWR, [(32.9, 21.0), (32.9, 38.5)]),
    ('POE_VDD', 'F.Cu', W_PWR, [(32.9, 38.5), (34.2, 38.5)]),
    # VSS rail: L10 pin 4 -> D10, C102, C101 -> U10 pins 4/5
    (VSS, 'F.Cu', W_PWR, [(30.8, 27.2), (42.6, 27.2)]),
    (VSS, 'F.Cu', 0.6, [(38.3, 27.2), (38.3, 25.3)]),
    (VSS, 'F.Cu', 0.6, [(40.4, 27.2), (40.4, 25.2)]),
    (VSS, 'F.Cu', W_NECK, [(42.6, 27.2), (44.2, 25.4)]),
    (VSS, 'F.Cu', W_SIG, [(44.67, 24.75), (44.2, 24.75), (44.2, 25.4), (44.67, 25.4)]),
    (VSS, 'F.Cu', 0.6, [(34.9, 27.2), (34.9, 29.0)]),
    (VSS, 'F.Cu', 0.4, [(41.6, 31.42), (41.6, 32.7)]),
    (VSS, 'F.Cu', 0.4, [(45.7, 30.42), (45.7, 31.7)]),
    (VSS, 'F.Cu', 0.4, [(48.0, 30.42), (48.0, 31.7)]),
    # DEN: pin 2 -> via -> B.Cu under the VDD neck -> via -> R100 pad 2
    ('/PoE PD/PD_DEN', 'F.Cu', W_SIG, [(44.67, 23.45), (43.9, 23.45), (42.2, 23.3)]),
    ('/PoE PD/PD_DEN', 'B.Cu', W_SIG, [(42.2, 23.3), (45.9, 20.4)]),
    ('/PoE PD/PD_DEN', 'F.Cu', W_SIG, [(45.9, 20.4), (45.22, 19.4)]),
    # CLSA: pin 3 -> via -> B.Cu under the VSS rail -> via -> R101 pad 1
    ('/PoE PD/PD_CLSA', 'F.Cu', W_SIG, [(44.67, 24.1), (43.9, 24.1), (42.6, 24.5)]),
    ('/PoE PD/PD_CLSA', 'B.Cu', W_SIG, [(42.6, 24.5), (41.0, 28.9)]),
    ('/PoE PD/PD_CLSA', 'F.Cu', W_SIG, [(41.0, 28.9), (41.6, 29.78)]),
    # CLSB, REF straight down to R102 / R103
    ('/PoE PD/PD_CLSB', 'F.Cu', W_SIG, [(45.7, 26.43), (45.7, 28.6)]),
    ('/PoE PD/PD_REF', 'F.Cu', W_SIG, [(46.35, 26.43), (46.35, 27.5), (48.0, 28.2), (48.0, 28.6)]),
    # PG -> R104 (CONV_SS through 0R) and TP41
    ('/PoE PD/PD_PG', 'F.Cu', W_SIG, [(49.33, 24.1), (53.78, 24.1)]),
    ('/PoE PD/PD_PG', 'F.Cu', W_SIG, [(55.6, 22.0), (54.3, 23.3), (53.78, 24.1)]),
    # VCOUT: pin 14 -> via -> B.Cu up to R105 / R106 and down to C104 / D11
    ('VCOUT', 'F.Cu', W_SIG, [(49.33, 23.45), (50.6, 23.45), (51.9, 23.0)]),
    ('VCOUT', 'B.Cu', W_SIG, [(51.9, 23.0), (51.9, 19.4), (40.7, 19.4)]),
    ('VCOUT', 'F.Cu', W_SIG, [(41.73, 18.82), (40.7, 19.4)]),
    ('VCOUT', 'F.Cu', W_SIG, [(49.73, 18.82), (50.6, 19.4)]),
    ('VCOUT', 'B.Cu', W_SIG, [(51.9, 23.0), (51.9, 27.0), (56.0, 27.0), (56.0, 30.4)]),
    ('VCOUT', 'F.Cu', W_SIG, [(54.8, 29.18), (56.0, 30.4)]),
    ('VCOUT', 'F.Cu', W_SIG, [(55.05, 31.6), (56.0, 30.4)]),
    # VCIN: pin 15 -> via -> B.Cu down -> via -> D11 pad 2 -> C103 pad 1
    ('VCIN', 'F.Cu', W_SIG, [(49.33, 22.8), (49.7, 22.8), (50.0, 22.4), (50.6, 21.6)]),
    ('VCIN', 'B.Cu', 0.4, [(50.6, 21.6), (50.6, 32.8), (52.95, 32.8)]),
    ('VCIN', 'F.Cu', W_SIG, [(52.95, 32.8), (52.95, 31.6), (53.2, 30.4), (53.2, 29.18)]),
    # TPH up to U11 pad 2; TPL round the right of U12 so it doesn't cross U12's LED link
    ('/PoE PD/PD_TPH', 'F.Cu', W_SIG, [(47.0, 21.77), (47.0, 17.4), (44.27, 16.2), (44.27, 14.26)]),
    ('/PoE PD/PD_TPL', 'F.Cu', W_SIG, [(47.65, 21.77), (47.65, 20.4), (53.6, 20.4), (53.6, 16.0),
                                       (52.27, 15.0), (52.27, 14.26)]),
    # LED drive: opto pad 1 straight down to R105 / R106 pad 2
    ('/PoE PD/TPH_LED_A', 'F.Cu', W_SIG, [(41.73, 14.26), (41.73, 17.18)]),
    ('/PoE PD/TPL_LED_A', 'F.Cu', W_SIG, [(49.73, 14.26), (49.73, 17.18)]),
    # PRI_RTN: pins 10-12 -> right along y 25.6 (C103 / C104 returns) -> down past D11 -> back to C105 pad 2
    ('PRI_RTN', 'F.Cu', W_SIG, [(49.33, 24.75), (49.8, 24.75), (49.8, 25.4), (49.33, 25.4)]),
    ('PRI_RTN', 'F.Cu', W_SIG, [(48.3, 26.43), (48.3, 26.9), (49.8, 26.9), (49.8, 25.4)]),
    ('PRI_RTN', 'F.Cu', W_NECK, [(49.8, 25.4), (50.6, 25.6)]),
    ('PRI_RTN', 'F.Cu', W_PWR, [(50.6, 25.6), (57.5, 25.6), (57.5, 35.8), (44.2, 35.8), (44.2, 37.5)]),
    ('PRI_RTN', 'F.Cu', 0.4, [(53.2, 25.6), (53.2, 27.3)]),
    ('PRI_RTN', 'F.Cu', 0.4, [(54.8, 25.6), (54.8, 27.3)]),
    # secondary strip: pull-ups to +3V3, GND between the two opto emitters (kept above the barrier band)
    ('POE_TPH_N', 'F.Cu', W_SIG, [(42.02, 1.6), (41.73, 3.0), (41.73, 4.74)]),
    ('POE_TPL_N', 'F.Cu', W_SIG, [(50.02, 1.6), (49.73, 3.0), (49.73, 4.74)]),
    ('+3V3', 'F.Cu', W_SIG, [(40.38, 1.6), (40.38, 0.3), (48.38, 0.3), (48.38, 1.6)]),
    ('GND', 'F.Cu', W_SIG, [(44.27, 4.74), (44.27, 6.1), (52.27, 6.1), (52.27, 4.74)]),
]

# Locked vias: (net, (x, y)). POE_IN nets get 0.8/0.4 mm, the rest 0.6/0.3 mm.
VIAS = [
    ('POE_VDD', (32.9, 21.0)), ('POE_VDD', (32.9, 38.5)),
    (VSS, (37.0, 27.2)), (VSS, (39.4, 27.2)),
    (VSS, (41.6, 32.7)), (VSS, (45.7, 31.7)), (VSS, (48.0, 31.7)),
    ('/PoE PD/PD_DEN', (42.2, 23.3)), ('/PoE PD/PD_DEN', (45.9, 20.4)),
    ('/PoE PD/PD_CLSA', (42.6, 24.5)), ('/PoE PD/PD_CLSA', (41.0, 28.9)),
    ('VCOUT', (51.9, 23.0)), ('VCOUT', (40.7, 19.4)), ('VCOUT', (50.6, 19.4)), ('VCOUT', (56.0, 30.4)),
    ('VCIN', (50.6, 21.6)), ('VCIN', (52.95, 32.8)),
]
POE_IN = {'POE_VDD', VSS, BR_P, BR_N, 'PR12', 'PR36', 'PR45', 'PR78', 'VCIN'}
VSS_STUBS = []
VSS_POUR = [(34.2, 22.4), (50.0, 22.4), (50.0, 33.4), (34.2, 33.4)]   # B.Cu


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


def clear(board):
    # Delete (not Remove): pcbnew's SWIG Remove() fails on zones and leaks tracks.
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
    missing = {fp.GetReference() for fp in board.GetFootprints()} - set(PLACE)
    if missing:
        raise SystemExit('no position for: ' + ' '.join(sorted(missing)))


def place_refs(board):
    """Designators on the silkscreen, readable and off pads: for each part try above, below, left and right of
    its courtyard (level, then turned 90 degrees) and keep the first spot clear of every pad, every other
    courtyard and the designators already placed, inside the outline. 1.0 mm text, 0.15 mm line."""
    def grow(box, mm):
        b = pcbnew.BOX2I(box.GetPosition(), box.GetSize())
        b.Inflate(pcbnew.FromMM(mm))
        return b

    fps = sorted(board.GetFootprints(), key=lambda f: f.GetReference())
    pads = [grow(p.GetBoundingBox(), 0.2) for f in fps for p in f.Pads()]
    crt = {f.GetReference(): f.GetCourtyard(pcbnew.F_CrtYd).BBox() for f in fps}
    # another part's body: its courtyard less 0.4 mm (a designator may sit on the courtyard margin, not on the body)
    body = {r: grow(b, -0.4) for r, b in crt.items()}
    x0, y0, x1, y1 = OUTLINE
    edge = pcbnew.BOX2I(P(x0 + 0.3, y0 + 0.3), pcbnew.VECTOR2I(pcbnew.FromMM(x1 - x0 - 0.6), pcbnew.FromMM(y1 - y0 - 0.6)))
    placed, unplaced = [], []
    own_silk = {f.GetReference(): [grow(g.GetBoundingBox(), 0.1) for g in f.GraphicalItems()
                                   if g.GetLayer() == pcbnew.F_SilkS] for f in fps}
    for f in fps:
        t = f.Reference()
        t.SetVisible(True)
        c = crt[f.GetReference()]
        cx, cy = c.GetCenter().x, c.GetCenter().y
        mm = pcbnew.FromMM
        spots = []
        for d in (0.6, 1.2, 2.0):
            for s in (0, -1.5, 1.5, -3.0, 3.0):
                spots += [(cx + mm(s), c.GetTop() - mm(d)), (cx + mm(s), c.GetBottom() + mm(d))]
            for s in (0, -1.5, 1.5):
                spots += [(c.GetLeft() - mm(d + 1.2), cy + mm(s)), (c.GetRight() + mm(d + 1.2), cy + mm(s))]
        ok = False
        # 1.0 mm text first; 0.8 mm (the workspace minimum) only where 1.0 mm has no clear spot
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
            t.SetVisible(False)      # left on F.Fab only; listed in BLOCK.md
            unplaced.append(f.GetReference())
    return unplaced


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        raise SystemExit(f'no net {name}')
    return n


def track(board, name, layer, width, pts):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(board.GetLayerID(layer))
        t.SetNet(net(board, name))
        t.SetLocked(True)
        board.Add(t)


def via(board, name, at):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(*at))
    big = name in POE_IN
    v.SetWidth(pcbnew.FromMM(0.8 if big else 0.6))
    v.SetDrill(pcbnew.FromMM(0.4 if big else 0.3))
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


def barrier(board):
    x0, _, x1, _ = OUTLINE
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetZoneName('isolation barrier 6 mm')
    z.Outline().AddOutline(polygon([(x0, BARRIER[0]), (x1, BARRIER[0]), (x1, BARRIER[1]), (x0, BARRIER[1])]))
    z.SetLocked(True)
    board.Add(z)


def vss_pour(board):
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.B_Cu)
    z.SetNet(net(board, VSS))
    z.SetLocalClearance(pcbnew.FromMM(0.6))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetZoneName('POE_VSS thermal pour')
    z.Outline().AddOutline(polygon(VSS_POUR))
    z.SetLocked(True)
    board.Add(z)


def prepare(path):
    board = pcbnew.LoadBoard(path)
    clear(board)
    place(board)
    outline(board)
    hidden = place_refs(board)
    if hidden:
        print('designators with no clear spot (hidden on silk, kept on F.Fab):', ' '.join(hidden))
    for name, layer, width, pts in TRACKS:
        track(board, name, layer, width, pts)
    for a, b in VSS_STUBS:
        track(board, VSS, 'F.Cu', 0.4, [a, b])
    for name, at in VIAS:
        via(board, name, at)
    barrier(board)
    vss_pour(board)
    pcbnew.SaveBoard(path, board)
    print(f'prepared {path}: {len(PLACE)} parts placed and locked, {len(TRACKS) + len(VSS_STUBS)} power runs, '
          f'{len(VIAS)} vias, barrier and VSS pour')


def finish(path):
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    print(f'zones filled: {path}')


def export_dsn(path, dsn):
    board = pcbnew.LoadBoard(path)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('DSN export failed')
    print(f'wrote {dsn}')


def import_ses(path, ses):
    board = pcbnew.LoadBoard(path)
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit('SES import failed')
    pcbnew.SaveBoard(path, board)
    print(f'imported {ses} into {path}')


if __name__ == '__main__':
    modes = {'prepare': (prepare, 3), 'finish': (finish, 3), 'export-dsn': (export_dsn, 4), 'import-ses': (import_ses, 4)}
    if len(sys.argv) < 3 or sys.argv[1] not in modes or len(sys.argv) != modes[sys.argv[1]][1]:
        raise SystemExit(__doc__ + '\n    ... export-dsn <pcb> <out.dsn> | import-ses <pcb> <in.ses>')
    modes[sys.argv[1]][0](*sys.argv[2:])
