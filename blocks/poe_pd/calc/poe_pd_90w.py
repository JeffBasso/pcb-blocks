"""poe_pd ratings at continuous 90 W at the PD (pcb-blocks poe_pd, LT4294 + LT4321, DC2583A design).

Case (Jeff, Ion-Speakers PR #20 and #15, "design to the extremes"):
  - 90 W at the PI from a Type 4 PSE at its 52 V minimum, short cable (no cable drop): 1.73 A
    (1.80 A at 50 V as a sensitivity row). IEEE 802.3bt PSE range 52-57 V: general knowledge, the
    standard isn't in the library.
  - Bridge: one pair set carries all of it (two FETs conduct: one top, one bottom).
  - Voltage derating at 57 V; thermal at 50 C air (wallnode-amp INTERFACES T1, the enclosure's worst
    case inside air); every FET's loss at its 175 C maximum Rds(on), so no Tj iteration flatters it.
Sources (page numbers are the PDF's):
  LT4294 Rev B; LT4321 Rev A; DC2583A demo manual Rev A; Nexperia PSMN075-100MSE and PSMN040-100MSE
  (26 Mar 2013); onsemi FOD814/FOD817 Rev 10; Vishay D/CRCW e3 (rev 14-Apr-2026); Diodes MMSZ5221B-
  MMSZ5259B; SMBJ5.0A-SMBJ200A; Wurth 744272251 rev 007.
Run: python -I calc/poe_pd_90w.py  (output committed as calc/poe_pd_90w_output.txt)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fet_copper as fc  # noqa: E402

# ---- the case -----------------------------------------------------------------------------------
P_PI = 90.0          # W, at the PI
V_PSE_MIN = 52.0     # V, Type 4 PSE minimum, short cable
V_MAX = 57.0         # V, port maximum (derating)
T_AIR = 50.0         # C
TJ_LIMIT = 125.0     # C, the design limit for every junction here (H-grade ICs: 125 C; FETs 175 C abs)


def i_load(p, v):
    return p / v


def fet_loss(i, rds):
    return i * i * rds


def rth_max(p, t_air, tj):
    """Largest junction-to-air thermal resistance that keeps Tj <= tj at loss p."""
    return (tj - t_air) / p


def inrush(igpu, cport, cgate):
    """LT4294 p8: IINRUSH = IGPU x CPORT / CGATE."""
    return igpu * cport / cgate


# LT4294 p3: IGPU 18-27 uA. CPORT: C105 100 uF +-20% (VKME). CGATE: 47 nF +-10%; the 250 V X7R's DC-bias
# loss at the gate's <= 75 V isn't in the datasheet in hand, so the upper bound halves CGATE as a margin.
def inrush_bounds(cport=100e-6, cgate=47e-9, cport_tol=0.20, cgate_tol=0.10, cgate_bias=0.5):
    lo = inrush(18e-6, cport * (1 - cport_tol), cgate * (1 + cgate_tol))
    hi = inrush(27e-6, cport * (1 + cport_tol), cgate * (1 - cgate_tol) * cgate_bias)
    return lo, hi


def cpd_bounds(caps):
    """caps: [(C, tol)]; returns (min, max) of the sum."""
    return (sum(cv * (1 - t) for cv, t in caps), sum(cv * (1 + t) for cv, t in caps))


def led_current(r, r_tol, v_range, vf, vol):
    """(min, max) LED current through r from a rail in v_range, LED VF range vf, sink VOL range vol."""
    lo = (v_range[0] - vf[1] - vol[1]) / (r * (1 + r_tol))
    hi = (v_range[1] - vf[0] - vol[0]) / (r * (1 - r_tol))
    return lo, hi


def r_power(v, r):
    return v * v / r


def fet_drop(i, rds):
    """LT4321 p8: forward drop VF = IAVG x Rds(on), to be 20-70 mV for the power saving."""
    return i * rds


# ---- off-state leakage vs the detection signature -------------------------------------------------------------
# PSMN040-100MSE p5 (and PSMN075-100MSE p5, the same limits): IDSS max 1 uA at 25 C and 500 uA at 175 C, VDS 100 V.
# Between the two, leakage is taken as exponential in temperature, and below 100 V as I100 x sqrt(V / 100)
# (junction generation current): both general knowledge, flagged. The sqrt law is the pessimistic choice here,
# because its slope dI/dV at the low detection voltages is ~3x an ohmic model's.
IDSS_25, IDSS_175 = 1e-6, 500e-6


def idss_at(t):
    return IDSS_25 * (IDSS_175 / IDSS_25) ** ((t - 25.0) / 150.0)


def leak_slope(i100, v, n):
    """dI/dV of n reverse-biased FETs at v volts, each leaking i100 at 100 V."""
    return n * i100 * (v / 100.0) ** 0.5 / (2.0 * v)


def parallel_sig(r_sig, g):
    return 1.0 / (1.0 / r_sig + g)


# LT4294 p3: VSIG 23.7-25.2 kohm (excludes the bridge, Note 2); the PSE measures dV/dI with two points in 2.7-10.1 V
# (p6). IEEE 802.3 accepts 19-26.5 kohm at the PSE and asks 23.75-26.25 kohm of the PD: general knowledge, the
# standard isn't in the library. During detection the LT4321 is shut down (OUTP < 12 V, p7-8) and its FETs' body
# diodes are the bridge: at most 4 of the 8 FETs are reverse-biased across the port (the other two of an active
# pair set, and, on a floating pair set, two in series, counted here as two to bound it).
V_DET_LO = 2.7
N_REVERSE = 4


# ---- copper per FET --------------------------------------------------------------------------------------------
# From the filled layout (layout_poe_pd.py; zone fills read back with pcbnew by tools in layout_poe_pd.py 'copper'):
# for each FET, the copper of its tab net on each layer within a 14 mm square centred on its tab (so a long strip
# isn't read as a big square, and nothing far away counts). The curves read the smallest layer's area as the square
# (each layer counted once: rev B's first table summed F.Cu and B.Cu and read the sum on the 2 oz curve, which
# counted the copper twice). Rows: (name, {layer: mm2}, loss kind, neighbour conducting within ~2 mm).
COPPER = []
CU_4L, CU_OUTER = 140, 70       # um summed: PCBWay 4L 1 oz x 4; and with no inner-layer credit (outer 1 oz + 1 oz)


def main():
    rows = []

    def row(part, check, result, verdict):
        rows.append((part, check, result, verdict))

    i = i_load(P_PI, V_PSE_MIN)
    i50 = i_load(P_PI, 50.0)
    print(f"Case: {P_PI:.0f} W at the PI from {V_PSE_MIN:.0f} V -> {i:.3f} A ({i50:.3f} A at 50 V); "
          f"derating at {V_MAX:.0f} V; {T_AIR:.0f} C air; Tj limit {TJ_LIMIT:.0f} C\n")

    # Bridge FETs and the hot-swap FET: all PSMN040-100MSE (Jeff, Ion-Speakers#15, 2026-11-19; DC2583A uses
    # PSMN075-100MSE in the bridge). 36.6 mohm max at 25 C (p5), a = 2.7 at 175 C (p8 Fig. 12) -> 98.8 mohm;
    # Rth(j-mb) 1.65 K/W max (p4); VDS 100 V (p1); VGS(th) 2.3-4 V at 25 C (p5), LT4321 asks >= 2 V (LT4321 p8).
    rds40 = 0.0366 * 2.7
    p40 = fet_loss(i, rds40)
    row('Q50-Q57 PSMN040-100MSE', f'loss at 175 C Rds(on) {rds40*1e3:.1f} mohm, one pair set ({i:.2f} A)',
        f'{p40:.3f} W each ({fet_loss(i50, rds40):.3f} W at 50 V); 2 conduct', 'see copper')
    vf = fet_drop(i50, 0.0366)
    row('', 'LT4321 p8: VF = IAVG x Rds(on) in 20-70 mV (36.6 mohm, 25 C max; 1.80 A)',
        f'{vf*1e3:.0f} mV (PSMN075, 71 mohm p5: {fet_drop(i50, 0.071)*1e3:.0f} mV)', 'PASS' if 0.020 <= vf <= 0.070 else 'FAIL')
    row('', 'VDS 100 V vs 57 V', f'{100/V_MAX:.2f}x', 'PASS (>= 1.5x)')
    row('', 'VGS(th) min 2.3 V (25 C) vs LT4321 >= 2 V', 'meets; 1 V min at 175 C (p5) as in ADI\'s own design',
        'PASS (as the reference)')
    row('', 'gate drive: TG 7.7-11 V, BG 10-13 V (LT4321 p3) vs VGS +-20 V (p2)', 'max 13 V', 'PASS')
    t_bg = 30e-9 / 15e-6
    row('', f'gate charge QG(tot) 30 nC (p6; PSMN075 16.4 nC) at BG pull-up 15 uA min (LT4321 p3)',
        f'<= {t_bg*1e3:.1f} ms to enhance (PSMN075 {16.4e-9/15e-6*1e3:.1f} ms); body diodes carry it meanwhile',
        'PASS (bridge on at ~28 V, long before the hot-swap)')
    for t_c, label in ((25.0, 'cold, 25 C'), (T_AIR, f'{T_AIR:.0f} C air, unpowered'),
                       (110.0, 'hot re-detect, 110 C (just after a 90 W port drop)')):
        g = leak_slope(idss_at(t_c), V_DET_LO, N_REVERSE)
        lo, hi = parallel_sig(23.7e3, g), parallel_sig(25.2e3, g)
        verdict = 'PASS' if lo >= 19e3 else 'FAIL'
        row('' if t_c != 25.0 else 'Detection: leakage', f'{N_REVERSE} FETs off, IDSS {idss_at(t_c)*1e6:.1f} uA at 100 V '
            f'({label}); slope at {V_DET_LO} V', f'{1/g/1e6:.2f} Mohm in parallel: VSIG 23.7-25.2k -> '
            f'{lo/1e3:.2f}-{hi/1e3:.2f}k ({lo/23.7e3-1:+.1%})', verdict + ' (PSE 19-26.5k)')
    row('', 'same IDSS limits as ADI\'s PSMN075-100MSE (p5 of both)', 'no change against DC2583A', 'PASS')
    row('Q58 PSMN040-100MSE', f'loss at 175 C Rds(on) {rds40*1e3:.1f} mohm (36.6 x 2.7, p5, p8 Fig. 12)',
        f'{p40:.3f} W ({fet_loss(i50, rds40):.3f} W at 50 V)', 'see copper')
    row('', f'Rth(j-a) for Tj <= {TJ_LIMIT:.0f} C', f'<= {rth_max(p40, T_AIR, TJ_LIMIT):.0f} K/W (j-mb 1.65)',
        'copper sized to this')
    row('', 'continuous current 1.73 A vs ID 21 A at Tmb 100 C (p2)', f'{i/21:.0%}', 'PASS')
    row('', 'VGS: HSGATE open-circuit 10-18 V above HSSRC (LT4294 p3) vs +-20 V', 'max 18 V', 'PASS')

    lo, hi = inrush_bounds()
    cport_v = 100e-6 * 1.2
    t_inrush = cport_v * V_MAX / lo
    row('Inrush (Q58, C104, R103)', 'IGPU 18-27 uA x CPORT 80-120 uF / CGATE 42.3-51.7 nF (x0.5 bias bound)',
        f'{lo*1e3:.0f}-{hi*1e3:.0f} mA, <= {t_inrush*1e3:.0f} ms to charge C105 alone', 'PASS (< 350 mA, LT4294 p9)')
    soa_dc = 0.55 * (175 - T_AIR) / (175 - 25)
    row('', f'Q58 SOA at 57 V: DC line ~0.55 A at Tmb 25 C (p4 Fig. 4), x{(175-T_AIR)/150:.2f} at Tmb {T_AIR:.0f} C',
        f'~{soa_dc:.2f} A DC vs {hi*1e3:.0f} mA', 'PASS (inside DC SOA)')
    row('', 'board load on POE_VDD adds to CPORT', 'the board recomputes inrush with its own input caps',
        'board check')

    cl, ch = cpd_bounds([(47e-9, 0.10), (47e-9, 0.10), (1e-9, 0.10), (1e-9, 0.10)])
    row('CPD: C102, C103 47 nF; C100, C101 1 nF', 'sum at +-10% vs 0.05-0.12 uF (LT4321 p8, IEEE)',
        f'{cl*1e6:.4f}-{ch*1e6:.4f} uF', 'PASS')
    row('MLCCs C100-C104', '250 V vs 57 V (CGATE sees <= 57 + 18 = 75 V)', f'{250/V_MAX:.1f}x / {250/75:.1f}x',
        'PASS (>= 2x)')
    row('C105 VKME 100 uF/100 V', 'voltage', f'{100/V_MAX:.2f}x', 'PASS (>= 1.25-1.5x)')

    # Class resistors: RCLASS operating voltage 1.32-1.43 V (LT4294 p3); held at a class event continuously.
    for ref, r, rated, pkg in (('R101 RCLS 49.9R', 49.9, 0.125, '0805'), ('R102 RCLS++ 118R', 118.0, 0.125, '0805')):
        pw = r_power(1.43, r * 0.99)
        row(ref, f'1.43 V held continuously; CRCW{pkg} {rated} W (D/CRCW e3 p2, the lower rating)',
            f'{pw*1e3:.1f} mW, {pw/rated:.0%}', 'PASS (<= 50%)')
    pr100 = (0.040 * 1.05 + 0.002) ** 2 * 8.2 * 1.05
    row('R100 8.2R 0805', 'class current 42 mA + 2 mA supply (p3) held', f'{pr100*1e3:.1f} mW, {pr100/0.125:.0%}',
        'PASS')

    # T2P opto: LED from POE_VDD through R105 33k 1%; FOD817 VF 1.0-1.4 V at ~1-2 mA (p5 Fig. 7, 25-110 C);
    # T2P VOL <= 0.8 V at 1 mA (LT4294 p3). PD-side voltage 37-57 V (DC2583A p2, port at RJ45).
    ilo, ihi = led_current(33e3, 0.01, (37.0, V_MAX), vf=(1.0, 1.4), vol=(0.0, 0.8))
    row('R105 33k / U11 LED', 'IF over 37-57 V', f'{ilo*1e3:.2f}-{ihi*1e3:.2f} mA', 'PASS (< 5 mA T2P abs max, p2)')
    p105 = r_power(V_MAX - 1.0, 33e3 * 0.99)
    row('R105 CRCW1206', '0.25 W (D/CRCW e3)', f'{p105*1e3:.0f} mW, {p105/0.25:.0%}', 'PASS (<= 50%)')
    # Secondary: R106 10k to 3.3 V, VCE(sat) 0.4 V -> needs 0.29 mA. CTR: FOD817A min 80% at 5 mA (p3);
    # at 1 mA the typical curve is ~0.7 of its 5 mA value (p5 Fig. 8); 0.95 for 50 C (p6 Fig. 11).
    i_need = (3.3 - 0.4) / (10e3 * 0.99)
    ic_min = ilo * 0.80 * 0.70 * 0.95
    row('U11 FOD817AS secondary', f'needs {i_need*1e3:.2f} mA (10k to 3.3 V)',
        f'min {ic_min*1e3:.2f} mA at IF {ilo*1e3:.2f} mA (CTR 80% x 0.70 x 0.95)', f'PASS ({ic_min/i_need:.1f}x)')
    row('', 'edges at 10k: ts + tf ~ 80 us (p6 Fig. 15) vs T2P period 1.01-1.45 ms (690-990 Hz, p3)',
        'low time reads up to ~8% long: 25% -> <= 33%, 50% -> <= 58%', 'decode bands in BLOCK.md')

    # EN Zener: MMSZ5252B 22.8-25.2 V (Diodes table); EN pull-down 160-310k (LT4321 p3); VIH 2.6 V.
    i_z = (V_MAX - 22.8) / 160e3
    row('D13 MMSZ5252B', 'enable threshold vs class range (<= 21 V, LT4294 p2)',
        f'EN high above {25.2+2.6:.1f} V max; off below 22.8 V min', 'PASS')
    row('', f'current {i_z*1e3:.2f} mA at 57 V', f'{i_z*25.2*1e3:.1f} mW of 500 mW', 'PASS')
    row('D10, D12 SMBJ58A', 'VRWM 58 V vs 57 V; clamp 93.6 V max vs 100 V abs max of LT4294/LT4321/FETs',
        'stand-off not derated (it would stop clamping)', 'PASS')
    row('L10 744272251', f'2.8 A rated (dT 40 K) vs {i:.2f} A', f'{2.8/i:.2f}x; {T_AIR + 40*(i/2.8)**2:.0f} C',
        'PASS (>= 1.2-1.3x)')
    p_u12 = 0.8e-3 * V_MAX
    row('U12 LT4321HUF', f'0.8 mA x 57 V (p3)', f'{p_u12*1e3:.0f} mW', 'PASS')
    row('U10 LT4294HDD', '2 mA x 57 V (p3); up to 1.5 W during classification, thermally protected (p10)',
        f'{2e-3*V_MAX*1e3:.0f} mW in operation', 'PASS')

    w = [max(len(r[k]) for r in rows) for k in range(4)]
    for r in rows:
        print('  '.join(r[k].ljust(w[k]) for k in range(4)).rstrip())
    total = 3 * p40
    print(f"\nFront-end FET loss, worst case: 3 x {p40:.3f} = {total:.2f} W "
          f"({total/P_PI:.1%} of 90 W); L10 DCR adds ~0.2 W.")

    p_fet = fet_loss(i50, rds40)
    print(f'\nBoard copper per FET (AN90003 Rev 5.0 Fig. 25 / Fig. 35 / Fig. 41, calc/fet_copper.py): {p_fet:.3f} W each '
          f'(175 C Rds(on), 50 V row), {T_AIR:.0f} C air; sized to {fc.T_SIZE:.0f} C with the 4 x 1 oz stack, and '
          f'<= {fc.T_PCB:.0f} C (PCB limit) with no inner-layer credit:')
    worst = 0.0
    for name, areas, neighbour in COPPER:
        outer = min(areas['F.Cu'], areas['B.Cu'])
        every = min(areas.values())
        t4 = fc.tj(fc.side(every), p_fet, CU_4L, neighbour)
        t2 = fc.tj(fc.side(outer), p_fet, CU_OUTER, neighbour)
        worst = max(worst, t2)
        layers = ' / '.join(f'{areas[k]:.0f}' for k in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'))
        verdict = 'PASS' if t4 <= fc.T_SIZE + 0.5 and t2 <= fc.T_PCB else 'FAIL'
        print(f"  {name:44} {layers:>22} mm2 -> {fc.side(every):4.1f} mm sq: Tj {t4:4.0f} C; "
              f"outer only {fc.side(outer):4.1f} mm sq: {t2:4.0f} C  {verdict}")
    print('  Layers F.Cu / In1.Cu / In2.Cu / B.Cu, each within a 14 mm square on the tab. "Outer only" is the bound Jeff '
          'set: inner layers give nothing, F.Cu + B.Cu read as one 2 oz layer.')
    print('  Re-check with kit #428\'s board thermal check once it exists, and with an IR picture at the highest grant '
          '(BRINGUP.md).')


if __name__ == '__main__':
    main()
