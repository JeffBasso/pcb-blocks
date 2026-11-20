# -*- coding: utf-8 -*-
"""poe_pd: IEEE 802.3bt PoE powered-device front end (pcb-blocks, CERN-OHL-P-2.0).

ADI's DC2583A design (Ethernet Alliance-certified 802.3bt PD): an LT4321 ideal-diode bridge with eight
PSMN040-100MSE FETs (DC2583A: PSMN075-100MSE), an input common-mode choke and TVS, and an LT4294 PD
controller driving a PSMN040-100MSE high-side hot-swap FET, set for Class 8. One FOD817AS optocoupler carries the LT4294's
T2P power-grant output (PWM-coded) across the isolation barrier. Every part is rated for continuous 90 W
at the PD (1.73 A from a 52 V Type 4 port on a short cable, one pair set carrying all of it). The drawn
sheet is the KiCad 10 design block pcb-blocks.kicad_blocks/poe_pd.kicad_block; tools/check-blocks.ps1
checks the two agree.

There is no PD current limit in this block (the LT4294 has none): a load that needs one adds it per output
(an eFuse or similar) on its own board. See BLOCK.md.

Status: drawn and parity-checked; not yet bench-proven. No compliance certification
(IEEE 802.3bt, safety or EMC) is claimed. See BLOCK.md.

Copy this file into a board's src/blocks/ with a first line
    # from pcb-blocks <tag or main> (<commit>)
and call poe_pd() from the board's board(). Symbols named pcb-blocks:... come from the library
pcb-skidl.ps1 adds (<Root>\\blocks\\lib).

Sources (BLOCK.md has the links): ADI LT4294 data sheet Rev B; ADI LT4321 data sheet Rev A; ADI DC2583A
demo manual Rev A (schematic and parts list), from which the stage is taken; Nexperia PSMN040-100MSE and
PSMN075-100MSE data sheets (26 Mar 2013); TI PMP20878 (the common-mode choke and the 1 nF caps).
"""
import builtins

from skidl import Net, Part, subcircuit

R_0603 = 'Resistor_SMD:R_0603_1608Metric'
R_0805 = 'Resistor_SMD:R_0805_2012Metric'
R_1206 = 'Resistor_SMD:R_1206_3216Metric'
C_0603 = 'Capacitor_SMD:C_0603_1608Metric'
C_1206 = 'Capacitor_SMD:C_1206_3216Metric'
LFPAK33 = 'Package_TO_SOT_SMD:LFPAK33'


def R(ref, value, mpn, footprint=R_0603):
    return Part('Device', 'R', ref=ref, value=value, footprint=footprint, fields={'MPN': mpn})


def C(ref, value, footprint=C_0603, mpn=None):
    fields = {'MPN': mpn} if mpn else {}
    return Part('Device', 'C', ref=ref, value=value, footprint=footprint, fields=fields)


def nfet(ref, mpn):
    """LFPAK33 N-FET: pins 1-3 S, 4 G, 5 D (mounting base) - Nexperia Table 2 (pinning)."""
    return Part('pcb-blocks', mpn, ref=ref, value=mpn, footprint=LFPAK33, fields={'MPN': mpn})


def no_connect(*pins):
    """No-connect flags (SKiDL's NC net, a builtin SKiDL sets up on import)."""
    nc = builtins.NC
    nc += pins


def pwr_flag(net):
    """A PWR_FLAG on net, as the drawn sheet has: ERC then sees the net as driven."""
    Part('power', 'PWR_FLAG', footprint='')[1] += net


@subcircuit
def poe_pd(PR12, PR36, PR45, PR78, POE_VDD, POE_VSS, PD_PWRGD, POE_T2P_N, _3V3, GND):
    """802.3bt PD front end (sheet "PoE PD").

    Ports (BLOCK.md has the ratings):
      PR12 PR36 PR45 PR78  the four magnetics centre taps (pairs 1-2, 3-6, 4-5, 7-8), 0-57 V
      POE_VDD              the switched + output to the load (the hot-swap FET's source, LT4294 HSSRC)
      POE_VSS              the - output and primary ground (LT4294 GND); not switched
      PD_PWRGD             open drain to POE_VSS, low until inrush is over (LT4294 PWRGD): hold the
                           load's converter off with it (RUN, SS/SD)
      POE_T2P_N            the PSE's power grant on the isolated side, active low, PWM-coded (LT4294 T2P
                           through the optocoupler), pulled up to _3V3
      _3V3, GND            the isolated (secondary) logic supply and ground
    On the drawn sheet POE_VSS, +3V3 and GND are power symbols (global nets by name); the other ports
    are hierarchical labels.
    """
    br_p, br_n = Net('BR_P'), Net('BR_N')             # LT4321 OUTP / OUTN, before the choke
    vport = Net('PD_VPORT')                            # after the choke, ahead of the hot-swap FET
    vpin = Net('PD_VPIN')                              # the LT4294 VPORT pin, behind its 8.2 ohm
    br_en = Net('PD_BR_EN')
    hsgate, cgate = Net('PD_HSGATE'), Net('PD_CGATE')
    rcls, rclspp = Net('PD_RCLS'), Net('PD_RCLSPP')
    t2p, t2p_led_a = Net('PD_T2P'), Net('T2P_LED_A')

    # source: LT4294 Rev B p16 (typical application) and DC2583A Rev A p9 (Q3-Q10, U2): the LT4321
    # ideal-diode bridge. Top FETs: drain to OUTP, source to the pair; bottom FETs: source to OUTN,
    # drain to the pair (LT4321 Rev A p5 pin functions). PSMN040-100MSE, 100 V (LT4321 p8: >= 100 V,
    # VGS(th) >= 2 V). DC2583A uses PSMN075-100MSE; PSMN040 (36.6 mohm max, p5) keeps LT4321 p8's 20-70 mV
    # drop at 1.80 A (66 mV, not 128 mV) and halves the loss (Jeff, Ion-Speakers#15, 2026-11-19).
    # pcb-blocks:LT4321 is KiCad's Power_Management:LT4321xUF with EN/~EN typed input and the stacked
    # OUTN pin split into 9 (OUTN) and 17 (EP), checked against LT4321 Rev A p2/p5.
    u12 = Part('pcb-blocks', 'LT4321', ref='U12', value='LT4321HUF#PBF',
               footprint='Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.65mm_EP2.15x2.15mm',
               fields={'MPN': 'LT4321HUF#PBF'})
    for pair, inp, tg, bg, top, bot in ((PR12, 'IN12', 'TG12', 'BG12', 'Q50', 'Q54'),
                                        (PR36, 'IN36', 'TG36', 'BG36', 'Q51', 'Q55'),
                                        (PR45, 'IN45', 'TG45', 'BG45', 'Q52', 'Q56'),
                                        (PR78, 'IN78', 'TG78', 'BG78', 'Q53', 'Q57')):
        n_tg, n_bg = Net('PD_' + tg), Net('PD_' + bg)
        pair += u12[inp]
        n_tg += u12[tg]
        n_bg += u12[bg]
        qt = nfet(top, 'PSMN040-100MSE')
        pair += qt['1'], qt['2'], qt['3']
        n_tg += qt['4']
        br_p += qt['5']
        qb = nfet(bot, 'PSMN040-100MSE')
        br_n += qb['1'], qb['2'], qb['3']
        n_bg += qb['4']
        pair += qb['5']
    br_p += u12['OUTP'], u12['~{EN}']                 # EN-bar tied to OUTP: enabled by EN (p5)
    br_n += u12['9'], u12['17']                       # OUTN and the exposed pad (= OUTN, p2)
    br_en += u12['EN']
    # source: LT4321 p8 (0.047 uF CPD split at each IC), p8 (TVS close to the LT4321).
    c100 = C('C100', '1nF/250V', mpn='CC0603KRX7RYBB102')
    c100[1, 2] += br_p, br_n
    c103 = C('C103', '47nF/250V', C_1206, mpn='CC1206KKX7RYBB473')
    c103[1, 2] += br_p, br_n
    d12 = Part('Device', 'D_Zener', ref='D12', value='SMBJ58A', footprint='Diode_SMD:D_SMB')
    d12[1, 2] += br_p, br_n

    # source: TI PMP20878 L10/C14/C15 (common-mode choke, kept for conducted emissions). With the choke
    # between the bridge and the controller, the LT4321 is enabled by a 24 V Zener from VPORT+ to EN
    # (LT4321 Rev A p8, p10 Fig. 5).
    l10 = Part('Device', 'L_Coupled', ref='L10', value='250uH 744272251',
               footprint='Inductor_SMD:L_CommonModeChoke_Wuerth_WE-SL5')
    br_p += l10['2']
    br_n += l10['3']
    vport += l10['1']
    POE_VSS += l10['4']
    d13 = Part('Device', 'D_Zener', ref='D13', value='MMSZ5252B 24V', footprint='Diode_SMD:D_SOD-123',
               fields={'MPN': 'MMSZ5252B-7-F'})
    d13[1, 2] += vport, br_en
    c101 = C('C101', '1nF/250V', mpn='CC0603KRX7RYBB102')
    c101[1, 2] += vport, POE_VSS

    # source: LT4294 Rev B p11 (TVS and 0.047 uF CPD1 close to VPORT/GND); DC2583A p8 (R12 8.2 ohm, C1, D2).
    d10 = Part('Device', 'D_Zener', ref='D10', value='SMBJ58A', footprint='Diode_SMD:D_SMB')
    d10[1, 2] += vport, POE_VSS
    r100 = R('R100', '8.2R', 'CRCW08058R20JNEA', R_0805)
    r100[1, 2] += vport, vpin
    c102 = C('C102', '47nF/250V', C_1206, mpn='CC1206KKX7RYBB473')
    c102[1, 2] += vpin, POE_VSS

    # source: LT4294 Rev B p2/p5 (pinout), p16 (typical application), DC2583A p8 (U1).
    u10 = Part('pcb-blocks', 'LT4294', ref='U10', value='LT4294HDD#PBF',
               footprint='Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm',
               fields={'MPN': 'LT4294HDD#PBF'})
    vpin += u10['10']
    POE_VSS += u10['1'], u10['5'], u10['11']
    POE_VSS += u10['2']                               # AUX: connect to GND when not used (p5)
    rcls += u10['3']
    rclspp += u10['4']
    hsgate += u10['9']
    POE_VDD += u10['8']
    PD_PWRGD += u10['7']
    t2p += u10['6']
    # source: LT4294 Table 2 p7 (Class 8: RCLS 49.9 ohm, RCLS++ 118 ohm, 1%); DC2583A RC4/RC13 (0805).
    r101 = R('R101', '49.9R 1%', 'CRCW080549R9FKEA', R_0805)
    r101[1, 2] += rcls, POE_VSS
    r102 = R('R102', '118R 1% (Class 8)', 'CRCW0805118RFKEA', R_0805)
    r102[1, 2] += rclspp, POE_VSS

    # source: LT4294 p8 Fig. 6 and p16 (high-side hot-swap FET, CGATE 47 nF + 3.3k to GND sets the inrush);
    # DC2583A Q1, C3, R13.
    q58 = nfet('Q58', 'PSMN040-100MSE')
    POE_VDD += q58['1'], q58['2'], q58['3']
    hsgate += q58['4']
    vport += q58['5']
    r103 = R('R103', '3.3k', 'CRCW06033K30JNEA')
    r103[1, 2] += hsgate, cgate
    c104 = C('C104', '47nF/250V', C_1206, mpn='CC1206KKX7RYBB473')
    c104[1, 2] += cgate, POE_VSS
    # source: LT4321 p8 (>= 10 uF across OUTP/OUTN once enabled, through the hot-swap FET); the output
    # bulk (CPORT in LT4294 p8).
    c105 = Part('Device', 'C_Polarized', ref='C105', value='100uF/100V VKME1452A101MV',
                footprint='Capacitor_SMD:CP_Elec_10x14.3')
    c105[1, 2] += POE_VDD, POE_VSS

    # source: LT4294 p3, p9 Table 3, p16 (T2P open drain to an opto). LED fed from POE_VDD through 33k
    # 1206 (IF 1.0-1.7 mA over 37-57 V, under T2P's 5 mA; 95 mW, 38% of 0.25 W): calc/poe_pd_90w.py.
    u11 = Part('Isolator', 'PC817', ref='U11', value='FOD817AS', footprint='Package_DIP:SMDIP-4_W9.53mm')
    r105 = R('R105', '33k', 'CRCW120633K0FKEA', R_1206)
    r105[1, 2] += POE_VDD, t2p_led_a
    u11[1, 2] += t2p_led_a, t2p
    u11[3, 4] += GND, POE_T2P_N
    r106 = R('R106', '10k', 'CRCW060310K0FKEA')
    r106[1, 2] += _3V3, POE_T2P_N

    # Test points aren't in the BOM (exclude_from_bom), as their symbols on the drawing.
    tp40 = Part('Connector', 'TestPoint', ref='TP40', value='POE_VSS (primary!)',
                footprint='TestPoint:TestPoint_Pad_D1.5mm', exclude_from_bom=True)
    tp40[1] += POE_VSS
    tp41 = Part('Connector', 'TestPoint', ref='TP41', value='PD_PWRGD (primary!)',
                footprint='TestPoint:TestPoint_Pad_D1.0mm', exclude_from_bom=True)
    tp41[1] += PD_PWRGD

    pwr_flag(POE_VSS)
    pwr_flag(vpin)          # the LT4294 VPORT pin, fed through R100 (passive)
    pwr_flag(POE_VDD)       # driven through the hot-swap FET (passive pins)
    for net in (PR12, PR36, PR45, PR78, br_p, br_n):
        pwr_flag(net)       # the LT4321's IN/OUT pins are power inputs; the magnetics and FETs are passive
