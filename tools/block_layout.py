"""block_layout.py: a block's PCB layout in its KiCad design block (pcb-blocks#2).

    python block_layout.py copy  <repo root> <block>   write the design block's layout from the test project
    python block_layout.py check <repo root> <block>   exit 1 if they differ

The layout lives in the block's test project, blocks/<block>/<block>.kicad_pcb, which has an Edge.Cuts outline
so it can be checked on its own (DRC). The design block keeps the same board without that outline -
pcb-blocks.kicad_blocks/<block>.kicad_block/<block>.kicad_pcb - so placing the block on a board doesn't add a
second outline. Nothing else is changed: every footprint, track, via, zone and drawing is copied as it is.
A block with no test-project board needs no layout; a design-block layout with no test-project board fails.

Standard library only (cut_sheet.py, next to this file, splits the file into its top-level items). Exit codes:
0 ok; 1 a problem (printed); 2 bad arguments.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut_sheet  # noqa: E402

DRAWINGS = {'gr_line', 'gr_rect', 'gr_arc', 'gr_circle', 'gr_poly', 'gr_curve', 'gr_bbox'}


def strip_edge_cuts(text):
    """text without its top-level Edge.Cuts drawings (CRLF is read as LF)."""
    text = text.replace('\r\n', '\n')
    head, chunks, tail = cut_sheet.split_top(text)
    keep = [c for kind, c in chunks if not (kind in DRAWINGS and re.search(r'\(layer "Edge\.Cuts"\)', c))]
    return head + ''.join(keep) + tail


def _paths(root, block):
    src = os.path.join(root, 'blocks', block, f'{block}.kicad_pcb')
    dst = os.path.join(root, 'pcb-blocks.kicad_blocks', f'{block}.kicad_block', f'{block}.kicad_pcb')
    return src, dst


def _read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def copy(root, block):
    src, dst = _paths(root, block)
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(strip_edge_cuts(_read(src)))
    return dst


def check(root, block):
    src, dst = _paths(root, block)
    have_src, have_dst = os.path.exists(src), os.path.exists(dst)
    if not have_src and not have_dst:
        return []
    if not have_src:
        return [f'{block}: the design block has a layout but has no blocks\\{block}\\{block}.kicad_pcb']
    if not have_dst:
        return [f'{block}: no layout in the design block (run tools\\block_layout.py copy . {block})']
    if strip_edge_cuts(_read(src)) != _read(dst).replace('\r\n', '\n'):
        return [f'{block}: the design block layout differs from blocks\\{block}\\{block}.kicad_pcb '
                f'(run tools\\block_layout.py copy . {block})']
    return []


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3 or argv[0] not in ('copy', 'check'):
        print(__doc__, file=sys.stderr)
        return 2
    cmd, root, block = argv
    if cmd == 'copy':
        print('wrote', copy(root, block))
        return 0
    problems = check(root, block)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
