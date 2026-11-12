# pcb-blocks

Reusable circuit blocks for KiCad 10. Each block is a SKiDL Python module (the checked list of
parts and nets) paired with a KiCad design block (the drawn sheet), and the two are checked against
each other.

**Status: drawn and parity-checked; not yet bench-proven. No compliance certification
(IEEE 802.3bt, safety or EMC) is claimed.** A block counts as proven only when its BRINGUP.md has
measurements from a built board. Until then it's a reviewed design, not a tested one.

## Blocks

| Block | What it is | Proven on | Status |
|---|---|---|---|
| [`poe_pd`](blocks/poe_pd/BLOCK.md) | IEEE 802.3bt PoE PD front end: Schottky bridges, CM choke and TVS, TPS2373-4 (Class 8), TPH/TPL over optocouplers | not yet (wallnode-amp rev A) | drawn, parity 0 |

## What's in a block

```
blocks/<name>/
  BLOCK.md                 what it is, its ports and ratings, sources and licence check, where it's proven
  BRINGUP.md               measurements from built boards (empty until it's built)
  src/blocks/<name>.py     the SKiDL module a board copies: @subcircuit <name>(ports...)
  src/<name>.py            test harness: wires the ports to named nets for the parity check
  <name>.kicad_sch         test project's top sheet: the block as one sheet, its ports to global labels
  <name>_sheet.kicad_sch   the drawn block
  <name>.png               the drawn block, for reading without KiCad
pcb-blocks.kicad_blocks/<name>.kicad_block/
  <name>.kicad_sch         KiCad design block: a byte-identical copy of <name>_sheet.kicad_sch
  <name>.json              its description, keywords and fields
lib/pcb-blocks.kicad_sym, lib/pcb-blocks.pretty/   symbols and footprints the blocks need beyond KiCad's own
```

## Using a block

With the [PCB design kit](https://github.com/JeffBasso/pcb-design-kit) installed, this repo is cloned
to `C:\dev\pcb\blocks`, and `pcb-blocks` is already in KiCad's design-block, symbol and footprint
tables. Without the kit, add those three yourself, pointing at this checkout.

1. Place the block from KiCad's Design Blocks panel as its own sheet.
2. Copy `blocks/<name>/src/blocks/<name>.py` into your board's SKiDL `src/blocks/`, with a first line
   `# from pcb-blocks <tag or main> (<commit>)` so you know which version you took.
3. Call it from your `board()` with your nets, and check the drawing and the Python agree (the kit's
   `pcb-skidl.ps1 <board> -Sheet "<sheet name>"`).

Pin to a commit: a later change here doesn't change your board. Blocks get tags (`poe-pd-v1.0`)
once they're bench-proven.

## Adding a block

1. Draw it and prove it on a board. It needs a code-first board (Python and drawing at parity 0)
   and bench measurements.
2. Cut its sheet out of the board with `tools/cut_sheet.py`, which also writes the test project's
   top sheet. Copy the board's module into `src/blocks/`, and write the harness `src/<name>.py`.
3. Copy `<name>_sheet.kicad_sch` into `pcb-blocks.kicad_blocks/<name>.kicad_block/<name>.kicad_sch`,
   and write `<name>.json`.
4. Run `tools\check-blocks.ps1` until every block passes. Then run the kit's
   `pcb-sch-junctions.ps1 blocks\<name> -Check` and `kicad-cli sch erc` on the block project, both
   with 0 errors.
5. Write BLOCK.md (all seven sections) and BRINGUP.md, and open a pull request.

The drawing and the Python change together, in the same commit, with `check-blocks.ps1` passing.

## Tools

- `tools/cut_sheet.py`: cuts a block out of a drawn sheet and refuses an unclean cut. Run it with the
  kit's SKiDL venv python, or any Python 3.10+. Tests: `python -m unittest discover -s tools`.
- `tools/check-blocks.ps1`: parity and the design-block copy check for every block. Needs the kit's
  `pcb-skidl.ps1` (`-Kit <folder>`, default `C:\dev\pcb`). Tests: `tools/check-blocks.Tests.ps1`
  (Pester 5).

## Licence

CERN Open Hardware Licence Version 2 - Permissive (CERN-OHL-P-2.0). See [LICENSE](LICENSE). Each
block's BLOCK.md records the sources it draws on and their terms. KiCad's stock symbols and
footprints are CC-BY-SA-4.0 with KiCad's exception for designs that use them.

The blocks are provided as is, with no warranty. You're responsible for checking a block against your
own requirements and for any certification your product needs.
