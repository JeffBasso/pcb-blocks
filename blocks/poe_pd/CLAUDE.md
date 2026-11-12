# poe_pd - block test project

Capture: skidl

This folder is the test project for the `poe_pd` block, not a board. `src/blocks/poe_pd.py` is the
module a board copies; `src/poe_pd.py` is the harness that wires its ports to named nets.
`poe_pd.kicad_sch` holds one sheet, "PoE PD" (`poe_pd_sheet.kicad_sch`), which is the drawn block;
`pcb-blocks.kicad_blocks/poe_pd.kicad_block/poe_pd.kicad_sch` is a byte-identical copy of it.

Check with `tools\check-blocks.ps1` from the repo root (parity 0 and the copy identical). Change the
drawing and the Python together, in the same commit. See BLOCK.md.
