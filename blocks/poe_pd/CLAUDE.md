# poe_pd - block test project

Capture: skidl

This folder is the test project for the `poe_pd` block, not a board. `src/blocks/poe_pd.py` is the
module a board copies; `src/poe_pd.py` is the harness that wires its ports to named nets.
`poe_pd.kicad_sch` holds one sheet, "PoE PD" (`poe_pd_sheet.kicad_sch`), which is the drawn block;
`pcb-blocks.kicad_blocks/poe_pd.kicad_block/poe_pd.kicad_sch` is a byte-identical copy of it.

Check with `tools\check-blocks.ps1` from the repo root (parity 0 and the copy identical). Change the
drawing and the Python together, in the same commit. See BLOCK.md.

The ratings are `calc/poe_pd_90w.py` (output committed; tests `python -I -m unittest discover -s calc`).

The layout is `poe_pd.kicad_pcb`, made by `layout_poe_pd.py` (KiCad's python: `prepare`, then `finish`);
change the script, not the board, then `python tools\block_layout.py copy . poe_pd` and DRC
(`kicad-cli pcb drc --refill-zones --schematic-parity`) to 0. BLOCK.md section 9 has the details.
