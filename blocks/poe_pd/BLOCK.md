# poe_pd: IEEE 802.3bt PoE powered-device front end

## 1. Status

**Drawn and parity-checked; not yet bench-proven. No compliance certification (IEEE 802.3bt,
safety or EMC) is claimed.**

Rev B of the block (2026-11-19, Ion-Speakers#15): ADI's LT4294 + LT4321 design (DC2583A), which replaces
rev A's TPS2373-4 and Schottky bridges. Jeff picked it after rev A's TPS2373-4 came out at 94% of its
current rating at 90 W, and its Schottky bridge at 173 C on the one-pair-set bound (Ion-Speakers PR #20 and
#15). Rev B is a reviewed design, not a measured one, until [BRINGUP.md](BRINGUP.md) has rows. ADI's
DC2583A is Ethernet Alliance-certified; this block is not, and it adds a common-mode choke DC2583A
doesn't have (section 5).

The block has a PCB layout (section 9): scripted, DRC-clean in the block's test project, with the FET copper
sized for the 90 W worst case. It hasn't been built.

## 2. What it is

The PD side of a PoE port, from the magnetics' centre taps to the load's input:

- an **LT4321 ideal-diode bridge** (U12) with eight **PSMN075-100MSE** FETs (Q50-Q57), so 2-pair and
  4-pair PSEs work without diode drops;
- an input common-mode choke (Würth 744272251, L10, from TI's PMP20878) with 1 nF caps either side.
  Because the choke sits between the bridge and the controller, the LT4321 is enabled by a 24 V Zener
  from VPORT+ (D13, LT4321 Fig. 5). There's a TVS at each IC (D12 at the LT4321, D10 at the LT4294) and
  a 47 nF CPD cap at each (C103, C102);
- an **LT4294** PD controller (U10), strapped for **Class 8** (RCLS 49.9R, RCLS++ 118R: 71.3 W at the PD
  after 5 class events, LT4294 Table 2 p7). It drives a **PSMN040-100MSE high-side hot-swap FET** (Q58).
  CGATE (47 nF + 3.3k, C104/R103) sets the inrush current, and PWRGD holds the load off until inrush is done;
- the **T2P** power-grant output carried across the isolation barrier by one FOD817AS optocoupler (U11),
  its LED fed from POE_VDD through 33k (R105), with a 10k pull-up (R106) to the isolated 3.3 V;
- the output bulk cap C105 (100 uF 100 V);
- two test points on the primary side, TP40 (POE_VSS) and TP41 (PD_PWRGD), which aren't in the BOM.

Every part is rated for **continuous 90 W at the PD** (section 5a).

**There is no PD current limit.** The LT4294 has none: it limits inrush only. A short after Q58 is cleared
by the PSE's port current limit and by the load's own limit (on wallnode-amp, the UCC2897A's cycle-by-cycle
limit). A board that splits POE_VDD into several outputs must limit each output itself, with an eFuse or
similar on that board, not in this block. The planned PoE wall power jack (3.3, 5, 12 and 24 V outlets)
is the first such board (Jeff, 2026-11-18).

![The drawn sheet](poe_pd.png)

## 3. Interface

| Port | On the sheet | Direction | Rating | Source |
|---|---|---|---|---|
| PR12, PR36, PR45, PR78 | hierarchical label | in | Magnetics centre taps, 0 to 57 V DC between pair sets | IEEE 802.3bt PSE range; LT4321 p5 |
| POE_VDD | hierarchical label | out | **Switched +**: the hot-swap FET's source (LT4294 HSSRC). 0-57 V; up to 71.3 W at the PD at Class 8, less when the PSE grants less (section 4). Parts rated for 90 W continuous, 1.73 A (section 5a) | LT4294 p5, p8, p16 |
| POE_VSS | power symbol (global) | out | The return and the primary ground (LT4294 GND); **not switched** | LT4294 p5, p16 |
| PD_PWRGD | hierarchical label | out | Open drain to POE_VSS (100 V, 5 mA abs max): low during classification and inrush, open once the hot-swap FET is fully on. Use it to hold the load off (RUN, SS/SD) | LT4294 p2, p9 |
| POE_T2P_N | hierarchical label | out | Open collector on the isolated side, 10k to +3V3; low when T2P is low. PWM-coded grant, section 4 | LT4294 p3, p9 Table 3 |
| +3V3, GND | power symbol (global) | in | The isolated (secondary) logic supply and ground for the opto output | |

The primary side (POE_VDD, POE_VSS) is isolated from the secondary (+3V3, GND, POE_T2P_N) only through the
optocoupler (FOD817, 5000 Vrms UL1577). The 1500 Vrms barrier itself is the board's job: creepage and
clearance at layout.

**Load inrush.** IINRUSH = IGPU x CPORT / CGATE (LT4294 p8). With C105 alone that's 28-153 mA (worst-case
bounds, section 5a). Everything on POE_VDD adds to CPORT, so a board recomputes it with its own input caps:
it must stay under 350 mA for the first 80 ms (p9), and inside Q58's SOA.

On a board, the power symbols join the board's own nets of the same name, so a board that calls its
3.3 V rail something else renames them.

## 4. Power negotiation (firmware rules)

The block asks for Class 8, but the switch decides what it gets. Whatever reads POE_T2P_N (an ESP32 on
wallnode-amp) has to follow these rules: nothing in the hardware stops the load drawing more than the grant.

### What the switch granted: T2P

LT4294 Table 3 (p9), for a Class 5-8 PD (RCLS++ fitted), and Table 4 (p10):

| T2P (low-impedance share of the period) | POE_T2P_N | Granted at the PD | When |
|---|---|---|---|
| 25% | low 25%, at 690-990 Hz | 71.3 W | Type 4 PSE, 5 class events: Class 8 granted |
| 50% | low 50%, at 690-990 Hz | 51 W | 4 events: a Type 3 PSE, or a Type 4 short of budget |
| always low | always low | 25.5 W | 2-3 events: an 802.3at (Type 2) PSE, or demoted |
| always high (Hi-Z) | always high | 13 W | 1 event: a Type 1 PSE, or demoted. Also what the pin reads before power-good |

T2P is driven after PWRGD is valid (p3). The opto stretches the low time: with the 10k pull-up, its
turn-off (storage + fall) is about 80 us (FOD817 p6 Fig. 15), so a 25% duty reads up to ~33% and 50% up to
~58% (calc/poe_pd_90w.py). The firmware decodes **over at least 4 periods**, and uses these bands:

| Measured low share | Grant |
|---|---|
| under 12% | 13 W (and "not known yet") |
| 12-42% | 71.3 W |
| 42-80% | 51 W |
| over 80% | 25.5 W |

It also checks that the period is 0.9-1.6 ms when it's toggling (690-990 Hz, plus margin). Anything else,
or two decodes that disagree, counts as the lowest grant.

Firmware rule:
1. Boot with the amp muted, or with its limiter at the idle tier.
2. Decode POE_T2P_N twice, a few periods apart, and use the grant only when both decodes agree.
3. Set the amp limiter so the whole board stays under the granted power (minus the board's own
   draw, converter losses included), then unmute (after the stagger below).
4. Keep decoding. If the grant drops, cut the limiter at once; if it rises, ramp up.

### Asking for less, then more: LLDP

After boot, the ESP32 uses 802.3bt Data Link Layer classification (LLDP) to ask the switch for
only what it needs, for example the idle tier, and asks again for more, up to the Class 8 ceiling,
when the music needs it. That frees switch budget for the other ports.

Checked against IEEE 802.3bt task force text (the published IEEE 802.3 standard itself is
paywalled and wasn't read):
- The request goes in the IEEE 802.3 Power via MDI TLV (an LLDP TLV, IEEE 802.3 Clause 79): the
  PD sends "PD requested power value" and the switch answers with "PSE allocated power value". Both
  are the maximum average input power at the PD's connector, in 0.1 W steps
  ([LLDP ad hoc baseline, 79.3.2.5-79.3.2.6](https://grouper.ieee.org/groups/802/3/bt/public/lldpadhoc/Baseline_for_review-LLDP_adhoc_Rev001.pdf)).
- Once DLL classification succeeds it takes precedence over the hardware class, and the assigned
  class follows the allocated value (621-999, that is 62.1-99.9 W, is Class 8). But "the Physical
  Layer classification of the PD is the maximum power that the PD draws across all output voltages
  and operational modes" ([yseboodt_05_0916](https://www.ieee802.org/3/bt/public/sep16/yseboodt_05_0916_dllclasschange.pdf),
  33.2.7). So the hardware Class 8 is the ceiling: LLDP can lower the grant and raise it again up
  to 71.3 W, never above it.

Firmware rule:
1. Lower the amp limiter first, then send the lower request.
2. To go up, send the request and raise the limiter only after the switch's PSE allocated power
   value comes back at the new figure. Never above the T2P grant.
3. T2P doesn't change with LLDP: it shows the hardware grant only. The firmware keeps the LLDP
   allocation itself and limits to the smaller of the two.
4. If LLDP never answers, the hardware grant is all there is.

This needs a managed switch that supports 802.3bt LLDP power (Power via MDI). An unmanaged switch
gets the hardware class only: T2P is the whole story, and the switch usually reserves the full class
for the port. ESP-IDF has no LLDP power agent that we know of, so the firmware sends and parses the
LLDPDUs itself (EtherType 0x88CC).

### Startup stagger

After a power cut or a switch reboot every node starts at once. So, after boot, a node doesn't
take power all at once:
1. It waits a delay worked out from its own MAC address (for example a hash of the MAC, modulo a
   few seconds in fixed steps): different on every node, and the same every time on one node. It
   waits before unmuting and before asking for more power over LLDP.
2. Then it ramps the amp limiter up gradually to the grant, rather than jumping to full, so the
   switch and the other nodes can adjust. Raises over LLDP go up in steps the same way. (Jeff
   prefers the ramp to a single step.)

Many managed switches already power their ports one after another, with a per-port power-up
delay. The node's own stagger comes on top of that; it doesn't replace it.

## 5. Sources and licence check

| Source | What was used | Terms |
|---|---|---|
| ADI LT4294 data sheet, Rev B (04/19) | Pinout, Class 8 resistors, hot-swap FET and CGATE, CPD split, TVS, PWRGD, T2P coding, typical application (p16) | ADI's data sheets are published for designing in its parts; values and topology reused in an original drawing, nothing reproduced. |
| ADI LT4321 data sheet, Rev A (07/22) | Pinout, MOSFET requirements, CPD, TVS, the Zener enable with a choke (Fig. 5 p10) | Same. |
| ADI DC2583A demo manual, Rev A (11/18) | The whole PD stage: schematic (p8-9) and parts list (p6-7), including R12 8.2R, C1/C3/C5, Q1/Q3-Q10 | Same; ADI's design files aren't redistributed here. |
| Nexperia PSMN040-100MSE and PSMN075-100MSE data sheets (26 Mar 2013) | Ratings, Rds(on) vs Tj, SOA, pinning | Nexperia data sheets; nothing copied. |
| Nexperia AN90003 Rev 5.0 (12 Feb 2026), LFPAK MOSFET thermal design guide | Rth(j-a) vs copper area for the FET pours (Fig. 25) | Nexperia application note; read, nothing copied. |
| TI PMP20878 (TIDRRG3B) | The common-mode choke and its two 1 nF caps, kept from rev A | TI Important Notice: use for development with TI products only, no reproduction. No TI part remains in this block; nothing from TI's documents is reproduced. |
| IEEE 802.3bt task force public documents (LLDP ad hoc baseline Rev001; yseboodt_05_0916) | The LLDP power rules in section 4 | Read and summarised in our own words, with short quotes; nothing copied. Read 2026-11-12. |
| KiCad 10 stock symbols and footprints (Device, Isolator, Connector, power; Diode_SMD, Capacitor_SMD, Resistor_SMD, Inductor_SMD, Package_DIP, Package_DFN_QFN, Package_TO_SOT_SMD, TestPoint) | Symbols and footprints | CC-BY-SA-4.0 with KiCad's exception: designs that use the libraries aren't bound by the licence. |
| `pcb-blocks:LT4294`, `pcb-blocks:LT4321`, `pcb-blocks:PSMN040-100MSE`, `pcb-blocks:PSMN075-100MSE` symbols | LT4294 drawn from its p2/p5 pin table. LT4321 is KiCad's `Power_Management:LT4321xUF` with EN/~EN typed input (KiCad's has ~EN as an output) and the stacked OUTN pin split into 9 and 17 (EP), so a SKiDL netlist can match it. The PSMN parts are KiCad's `BUK9M53-60EX` LFPAK33 symbol renamed (pins 1-3 S, 4 G, 5 D, as Nexperia's pinning table) | CERN-OHL-P-2.0 with the rest of this repo (the derived symbols keep KiCad's licence exception). |

Deviations from DC2583A:
- **Common-mode choke kept** (L10 with C100/C101, from PMP20878), for conducted emissions from the load's
  converter. With it, the LT4321 is enabled by a 24 V Zener from VPORT+ to EN (LT4321 Fig. 5), not by
  PWRGD (DC2583A R18), and each IC gets its own TVS (D12, D10) and 47 nF CPD.
- **H-grade ICs** (LT4294HDD, LT4321HUF; 125 C) in place of DC2583A's I-grade (85 C).
- **All port MLCCs are 250 V** (DC2583A: 100 V) for the 2x rule at 57 V; CGATE sees up to 75 V.
- AUX is tied to GND (unused, LT4294 p5); DC2583A's auxiliary input, its LED and its lab-test FET (Q11) are left out.
- The class resistors are fixed for Class 8 (DC2583A has a jumper bank).
- T2P drives an optocoupler (LT4294 p16 shows "OPTO"), LED from POE_VDD through 33k.

## 5a. Ratings at 90 W

The block is rated for the worst case, not the 71.3 W IEEE PD figure: **90 W continuous at the PD**, the full
Class 8 PSE budget arriving on a short cable. The lowest Type 4 PSE port voltage is 52 V (IEEE 802.3bt; the
standard wasn't read), so the current is 90 / 52 = **1.73 A** (1.80 A at 50 V). In the bridge, **one pair
set carries all of it**. Derating is at 57 V and the air at the board is 50 C. Every FET's loss uses its
**175 C maximum Rds(on)**. The workspace section 5 rules apply. The numbers and their pages are in
[`calc/poe_pd_90w.py`](calc/poe_pd_90w.py) (output committed); the summary:

| Part | Check | Result |
|---|---|---|
| Q50-Q57 PSMN075-100MSE | 1.73 A x 192 mohm (175 C max, p5) = 0.575 W (0.622 W at 50 V), two conduct; 100 V vs 57 V | 1.75x; Tj with the block's copper below |
| Q58 PSMN040-100MSE | 36.6 mohm x 2.7 (Fig. 12) = 98.8 mohm: 0.30 W; 1.73 A vs 21 A at Tmb 100 C | 8% |
| Inrush (Q58, C104, R103) | IGPU 18-27 uA x C105 80-120 uF / CGATE 42-52 nF, with CGATE halved again as a DC-bias bound: 28-153 mA | < 350 mA; inside Q58's DC SOA (~0.46 A at 57 V, Tmb 50 C) |
| CPD (C100-C103) | 2 x 47 nF + 2 x 1 nF at +-10%: 0.086-0.106 uF | inside 0.05-0.12 uF |
| MLCCs | 250 V vs 57 V (CGATE: vs 75 V) | 4.4x / 3.3x |
| C105 VKME 100 uF 100 V | 1.75x | pass |
| R101 RCLS, R102 RCLS++ | 1.43 V held continuously (a PSE stuck in classification): 41 mW / 17.5 mW, CRCW0805 at its lower 0.125 W rating | 33% / 14% |
| R100 8.2R | 44 mA held: 17 mW | 13% |
| R105 33k 1206 | LED 1.04-1.71 mA over 37-57 V (T2P 5 mA abs max); 96 mW of 0.25 W | 38% |
| U11 FOD817AS | needs 0.29 mA into 10k; CTR 80% min x 0.70 at 1 mA x 0.95 at 50 C gives 0.56 mA | 1.9x |
| D13 MMSZ5252B | EN on above 27.8 V max, off below 22.8 V (class range ends at 21 V); 5 mW | pass |
| D10, D12 SMBJ58A | VRWM 58 V; clamp 93.6 V vs 100 V abs max of the ICs and FETs | pass |
| L10 744272251 | 2.8 A vs 1.73 A: 1.62x, 65 C | pass |
| U12 LT4321, U10 LT4294 | 46 mW / 114 mW in operation; the LT4294 is thermally protected during classification (up to 1.5 W, p10) | pass |

**Copper per FET** (layout, section 9; Nexperia AN90003 Fig. 25, LFPAK33 on one 2 oz layer, 0.5 W curve):

| FET | Pour (F.Cu + B.Cu, 1 oz each) | Rth(j-a) | Tj at 0.62 W (Q58: 0.32 W), 50 C air |
|---|---|---|---|
| Q50-Q53 (BR_P strip, shared; one conducts) | 2099 mm2 | ~51 K/W | ~81 C |
| Q55, row 36 (worst row) | 413 mm2 | ~95 K/W | ~109 C |
| Q54, row 12 | 674 mm2 | ~77 K/W | ~98 C |
| Q56, row 45 | 760 mm2 | ~73 K/W | ~95 C |
| Q57, row 78 | 1035 mm2 | ~63 K/W | ~89 C |
| Q58 (VPORT band) | 705 mm2 | ~76 K/W | ~74 C |

All are under the FR4 120 C limit AN90003 marks and the 125 C design limit, with copper alone: no heat sink
and no thermal pad. Fig. 25 is one 2 oz layer; the block has two stitched 1 oz layers of the same outline,
and taking their summed area as that layer is a judgement. A host board's inner planes only add to it.
Re-check with the kit's board thermal check (pcb-design-kit#428) once it exists, and with an IR picture
at the highest grant (BRINGUP.md).

Resistor MPNs are Vishay CRCW; any 1%, 100 ppm thick-film part of the same size and at least the same P70 can
stand in. MLCC MPNs are Yageo, from the JLCPCB/LCSC catalog: the voltage and dielectric are the requirement,
the make isn't. **Do not substitute:** I-grade LT4294/LT4321 (85 C), and FETs with less than 100 V or
VGS(th) min under 2 V (LT4321 p8).

## 6. Proven on

Not yet. The first board is **wallnode-amp rev A** (Ion-Speakers), not built yet. When it's
measured, this section gets the board and rev, a link to the bring-up data in
[BRINGUP.md](BRINGUP.md), the load it was tested at, and any errata.

## 7. Using it

1. In KiCad 10, place `poe_pd` from the Design Blocks panel (library `pcb-blocks`) as a sheet
   named `PoE PD`. The kit's installer registers the library; without the kit, add
   `pcb-blocks.kicad_blocks` to the design-block library table, and `lib/pcb-blocks.kicad_sym` and
   `lib/pcb-blocks.pretty` to the symbol and footprint tables.
2. Copy `src/blocks/poe_pd.py` into the board's `src/blocks/`. Its first line is
   `# from pcb-blocks <tag or main> (<commit>)`. Add a SOURCES.md line with the repo URL and commit.
3. Call `poe_pd(...)` from the board's `board()` with the board's nets: the load's input on POE_VDD and
   POE_VSS, and PD_PWRGD to whatever holds the load off (a converter's RUN or soft-start).
4. Run `pcb-skidl.ps1 <board> -Sheet "PoE PD"` until it reports 0 differences.
5. Recompute the inrush with the board's own input capacitance on POE_VDD (section 3).
6. Bring the layout across (section 9): `pcb-blocks.kicad_blocks/poe_pd.kicad_block/poe_pd.kicad_pcb`,
   applied as one group to the board's 30 footprints, matched by reference.

The load (converter), the magnetics, any per-output current limiting, and the board's own isolation barrier
(the moat, inner planes and pours) are the board's.

## 8. Parity

`tools\check-blocks.ps1`, 2026-11-19 (skidl 3.0.0, KiCad 10.0.6):

```
--- poe_pd
  Python: 30 parts, 29 nets (+0 unconnected pins)   schematic: 30 parts, 29 nets (+0 unconnected pins)
  differences: 0
  nets with the same pins but a different name (not a difference): 19
  Parity: 0 differences.
poe_pd: parity 0, design block identical, layout identical
All 1 block(s) pass.
```

The 19 renamed nets are the local nets inside the sheet, which KiCad prefixes with `/PoE PD/`.

`kicad-cli sch erc` on the block project: 0 errors, 0 warnings.

## 9. Layout

`poe_pd.kicad_pcb` in this folder is the block's test-project board; the design block holds the same board
without its outline (`pcb-blocks.kicad_blocks/poe_pd.kicad_block/poe_pd.kicad_pcb`, written and checked by
`tools/block_layout.py`; `tools/check-blocks.ps1` fails if they differ).

![The layout](poe_pd_layout.png)

**How it was made (Ion-Speakers#15, 2026-11-19).** Everything is scripted with KiCad 10's pcbnew Python in
`layout_poe_pd.py` (`prepare` places, routes, pours and fills; `finish` refills). **Nothing is autorouted.**
Freerouting can't apply the fine-pitch fan-out exception below, so every track, via and zone is written in the
script, which checks the pad positions it was written against before it draws anything.

| | |
|---|---|
| Size | 130 x 74 mm outline (the test project's), parts on the top side only. Rev A's was 62 x 45 mm: the growth is the FET copper for the 90 W worst case |
| Copper | F.Cu and B.Cu only, so the block sits on a 2-, 4- or 6-layer board; inner layers are the board's |
| Bridge | four pair rows (12, 36, gap, 45, 78), each a PR pour of 43.8 x 12 mm on both layers. A BR_P strip runs down the left, with a band along the top to L10; a BR_N strip runs down the right. Each row's top FET is on the left edge (tab in the BR_P strip, sources in the row) and its bottom FET on the right edge (tab in the row, sources in the BR_N strip) |
| LT4321 | in the gap between the pair sets. Gate drives and pair senses fan out on F.Cu to vias and run on B.Cu (TG down the left, BG down the right), so the F.Cu pours stay whole; OUTP reaches the BR_P band on an F.Cu riser at x 40 |
| Power path | pours on both layers, via-stitched (~220 vias: 0.8/0.4 mm on POE nets, 0.6/0.3 mm on signals); short 0.5-1.0 mm stubs where a pad meets a pour. The worst case is 1.73 A; IPC-2221 external, 10 C rise, 1 oz needs ~0.64 mm |
| FET copper | section 5a: every conducting FET at or under ~109 C at 50 C air |
| PD section | L10 -> VPORT band (top) with D10, C101, D13 and Q58's tab -> POE_VDD pour (Q58's sources, C105+, R105) -> VSS pour (U10, the class resistors, C102, C104, C105-) |
| U10 | the plain DFN-10 footprint (no vias in the exposed pad, CLAUDE.md section 7); its pad joins the VSS pour on F.Cu |
| Clearances | POE_IN nets (POE_VDD, POE_VSS, BR_P/N, PR12-PR78, PD_VPORT, PD_VPIN) 0.6 mm (IPC-2221 Table 6-1 B2, 31-150 V). 0.25 mm inside the LT4321 and LT4294 fan-out areas (rule areas `FANOUT_U12`, `FANOUT_U10`) and the FET courtyards: functional insulation inside the primary circuit, at no less than the parts' own pad gaps. Other nets 0.15 mm. In `poe_pd.kicad_dru` and the project's netclasses |
| Isolation barrier | a 6 mm keep-out band (no tracks, vias or pours, F.Cu and B.Cu) under U11, and a DRC rule: secondary nets (+3V3, GND, POE_T2P_N) keep 6 mm clearance and creepage from everything else. 6 mm is wallnode-amp's moat placeholder until IEC 62368-1 is in the library; the FOD817 pads are 7.52 mm apart |
| Ports | the pads themselves: PR12-PR78 on the FETs' PR copper, POE_VDD and POE_VSS on C105's pads, PD_PWRGD on TP41, POE_T2P_N / +3V3 / GND on R106 and U11's output pins (right edge) |
| Checks | DRC (`kicad-cli pcb drc --refill-zones --schematic-parity`): 0 errors, 0 warnings, 0 unconnected, parity 0 |

A board that places the block keeps its own barrier: the band has to line up with the board's moat, and no
inner-layer plane may run under the band or join the two sides.
