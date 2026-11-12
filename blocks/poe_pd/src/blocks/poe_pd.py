# -*- coding: utf-8 -*-
"""poe_pd: IEEE 802.3bt PoE powered-device front end (pcb-blocks, CERN-OHL-P-2.0).

Two PDS5100 Schottky bridges, input common-mode choke and TVS, a TPS2373-4 for detection,
classification and hot-swap, and two FOD817AS optocouplers that carry the TPH/TPL power-class
outputs across the isolation barrier. The drawn sheet is the KiCad 10 design block
pcb-blocks.kicad_blocks/poe_pd.kicad_block; tools/check-blocks.ps1 checks the two agree.

Status: drawn and parity-checked; not yet bench-proven. No compliance certification
(IEEE 802.3bt, safety or EMC) is claimed. See BLOCK.md.

Copy this file into a board's src/blocks/ with a first line
    # from pcb-blocks <tag or main> (<commit>)
and call poe_pd() from the board's board(). Symbols named pcb-blocks:... come from the library
pcb-skidl.ps1 adds (<Root>\\blocks\\lib).

Sources (BLOCK.md has the links): TI SLUSCD1C (TPS2373 datasheet, Rev C); TI PMP20878 (TIDRRG3B
schematic, TIDUDB0 test report), from which the PD stage is taken; TI TIDA-050023 (TIDUEL2).
"""
import builtins

from skidl import Net, Part, subcircuit

R_0603 = 'Resistor_SMD:R_0603_1608Metric'
C_0603 = 'Capacitor_SMD:C_0603_1608Metric'
C_0805 = 'Capacitor_SMD:C_0805_2012Metric'


def R(ref, value, footprint=R_0603):
    return Part('Device', 'R', ref=ref, value=value, footprint=footprint)


def C(ref, value, footprint=C_0603):
    return Part('Device', 'C', ref=ref, value=value, footprint=footprint)


def no_connect(*pins):
    """No-connect flags (SKiDL's NC net, a builtin SKiDL sets up on import)."""
    nc = builtins.NC
    nc += pins


def pwr_flag(net):
    """A PWR_FLAG on net, as the drawn sheet has: ERC then sees the net as driven."""
    Part('power', 'PWR_FLAG', footprint='')[1] += net


@subcircuit
def poe_pd(PR12, PR36, PR45, PR78, POE_VDD, PRI_RTN, VCIN, VCOUT, CONV_SS,
           POE_TPH_N, POE_TPL_N, _3V3, GND):
    """802.3bt PD front end (sheet "PoE PD").

    Ports (BLOCK.md has the ratings):
      PR12 PR36 PR45 PR78  the four magnetics centre taps (pairs 1-2, 3-6, 4-5, 7-8), 0-57 V
      POE_VDD, PRI_RTN     to the DC-DC converter: VDD and the switched return (after the
                           TPS2373-4 hot-swap FET)
      VCIN, VCOUT          the converter's bias winding in, and the PD's bias out (VC_IN/VC_OUT)
      CONV_SS              the converter's soft-start, held low until PG (0 ohm R104)
      POE_TPH_N, POE_TPL_N open-collector power-class outputs on the isolated side, pulled to _3V3
      _3V3, GND            the isolated (secondary) logic supply and ground
    On the drawn sheet PRI_RTN, VCOUT, +3V3 and GND are power symbols (global nets by name); the
    other ports are hierarchical labels.
    """
    br_p, br_n = Net('BR_P'), Net('BR_N')
    poe_vss = Net('POE_VSS')
    den, clsa, clsb, ref = Net('PD_DEN'), Net('PD_CLSA'), Net('PD_CLSB'), Net('PD_REF')
    pg, tph, tpl = Net('PD_PG'), Net('PD_TPH'), Net('PD_TPL')
    tph_led_a, tpl_led_a = Net('TPH_LED_A'), Net('TPL_LED_A')

    # source: PMP20878 Schottky bridge option (8 x PDS5100); SLUSCD1C 8.2.2.1 p33 (bridges).
    for pair, hi, lo in ((PR12, 'D50', 'D54'), (PR36, 'D51', 'D55'),
                         (PR45, 'D52', 'D56'), (PR78, 'D53', 'D57')):
        d_hi = Part('Device', 'D_Schottky', ref=hi, value='PDS5100-13', footprint='Diode_SMD:D_PowerDI-5')
        d_lo = Part('Device', 'D_Schottky', ref=lo, value='PDS5100-13', footprint='Diode_SMD:D_PowerDI-5')
        br_p += d_hi['1']
        pair += d_hi['2'], d_lo['1']
        br_n += d_lo['2']

    # source: PMP20878 C14, L10, C15, D17, C29 (input filter); SLUSCD1C 8.2.2.2 p33 (TVS).
    l10 = Part('Device', 'L_Coupled', ref='L10', value='250uH 744272251',
               footprint='Inductor_SMD:L_CommonModeChoke_Wuerth_WE-SL5')
    br_p += l10['2']
    br_n += l10['3']
    POE_VDD += l10['1']
    poe_vss += l10['4']
    c100 = C('C100', '1nF/100V')
    c100[1, 2] += br_p, br_n
    c101 = C('C101', '1nF/100V')
    c101[1, 2] += POE_VDD, poe_vss
    c102 = C('C102', '0.1uF/100V', C_0805)
    c102[1, 2] += POE_VDD, poe_vss
    d10 = Part('Device', 'D_Zener', ref='D10', value='SMBJ58A', footprint='Diode_SMD:D_SMB')
    d10[1, 2] += POE_VDD, poe_vss
    # source: PMP20878 C28 (VDD-RTN bulk). C102 above: SLUSCD1C 8.2.2.3 p33 (0.1 uF 100 V VDD-VSS).
    c105 = Part('Device', 'C_Polarized', ref='C105', value='100uF/100V VKME1452A101MV',
                footprint='Capacitor_SMD:CP_Elec_10x14.3')
    c105[1, 2] += POE_VDD, PRI_RTN

    # source: SLUSCD1C p4 pin table (symbol and pinout); PMP20878 sheet 2.
    u10 = Part('pcb-blocks', 'TPS2373-4', ref='U10', value='TPS2373-4RGWR',
               footprint='pcb-blocks:TI_RGW0020B_VQFN-20-1EP_5x5mm_P0.65mm_EP2.2x2.2mm_ThermalVias')
    POE_VDD += u10['1']
    poe_vss += u10['4'], u10['5'], u10['21']
    PRI_RTN += u10['10'], u10['11'], u10['12']      # APD tied to RTN when unused (pin table)
    den += u10['2']
    clsa += u10['3']
    clsb += u10['6']
    ref += u10['7']
    pg += u10['13']
    VCOUT += u10['14']
    VCIN += u10['15']
    tpl += u10['17']
    tph += u10['18']
    no_connect(u10['8'], u10['9'], u10['16'], u10['19'])   # AMPS_CTL, MPS_DUTY, UVLO_SEL, BT unused

    # source: SLUSCD1C 8.2.2.4 p34 (RDEN 24.9k); Table 1 p18 (Class 6 = 63.4R + 249R; Class 8 = 63.4R + 90.9R).
    r100 = R('R100', '24.9k 1%')
    r100[1, 2] += POE_VDD, den
    r101 = R('R101', '63.4R 1%')
    r101[1, 2] += clsa, poe_vss
    r102 = R('R102', '249R 1% (Class 6; 90.9R = Class 8)')
    r102[1, 2] += clsb, poe_vss
    # source: SLUSCD1C p4 pin table (REF 49.9k 1% to VSS).
    r103 = R('R103', '49.9k 1%')
    r103[1, 2] += ref, poe_vss
    # source: PMP20878 R66 (PG -> converter SS/SD through 0 ohm).
    r104 = R('R104', '0R')
    r104[1, 2] += pg, CONV_SS
    # Test points aren't in the BOM (exclude_from_bom), as their symbols on the drawing.
    tp40 = Part('Connector', 'TestPoint', ref='TP40', value='POE_VSS (primary!)',
                footprint='TestPoint:TestPoint_Pad_D1.5mm', exclude_from_bom=True)
    tp40[1] += poe_vss
    tp41 = Part('Connector', 'TestPoint', ref='TP41', value='PD_PG (primary!)',
                footprint='TestPoint:TestPoint_Pad_D1.0mm', exclude_from_bom=True)
    tp41[1] += pg

    # source: PMP20878 D102, C64, C65; SLUSCD1C 8.2.2.8 p35 (C_VC_OUT >= 10 x C_VC_IN).
    d11 = Part('Device', 'D', ref='D11', value='MMDL914', footprint='Diode_SMD:D_SOD-323')
    d11[1, 2] += VCOUT, VCIN
    c103 = C('C103', '10nF/50V')
    c103[1, 2] += VCIN, PRI_RTN
    c104 = C('C104', '0.1uF/50V')
    c104[1, 2] += VCOUT, PRI_RTN

    # source: SLUSCD1C 8.2.2.7 p34-35 (TPH/TPL opto drive from VC_OUT, under 3 mA); FOD817A CTR 80-160%.
    for opto, led_r, pull, led_a, k, out in (('U11', 'R105', 'R107', tph_led_a, tph, POE_TPH_N),
                                             ('U12', 'R106', 'R108', tpl_led_a, tpl, POE_TPL_N)):
        u = Part('Isolator', 'PC817', ref=opto, value='FOD817AS', footprint='Package_DIP:SMDIP-4_W9.53mm')
        r_led = R(led_r, '5.36k')
        r_led[1, 2] += VCOUT, led_a
        u[1, 2] += led_a, k
        u[3, 4] += GND, out
        r_pu = R(pull, '10k')
        r_pu[1, 2] += _3V3, out

    pwr_flag(POE_VDD)
    pwr_flag(poe_vss)
    pwr_flag(PRI_RTN)       # driven through the TPS2373-4's RTN (hot-swap FET), a passive pin
