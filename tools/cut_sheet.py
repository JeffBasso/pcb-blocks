"""cut_sheet.py: cut one block out of a drawn KiCad 10 schematic sheet, for pcb-blocks.

    python cut_sheet.py <in.kicad_sch> <out.kicad_sch> --keep <refs.txt> --ports A,B,...
        --rename old=new --project <name> --root-uuid <uuid> --sheet-uuid <uuid> --title <text>
        [--margin 15] [--top <top.kicad_sch> --sheet-name <name> [--flag <power net>]...]

The block is the listed parts (--keep, one reference per line) and everything drawn around them:
the box round the listed parts, grown by --margin mm, holds the block. Inside it, power symbols and
PWR_FLAGs (# references), wires, junctions, labels, no-connects and notes are kept; everything
outside is dropped. The cut has to be clean, or nothing is written (exit 1):
  - every listed part is on the sheet, and no other part sits inside the box;
  - no wire runs from inside the box to outside it;
  - every global label inside the box is a port (--ports); it becomes a hierarchical label.
Then lib ids, embedded symbols and Footprint fields are renamed (--rename, e.g. wallnode-amp=pcb-blocks),
embedded symbols nothing uses are dropped, instance paths are rewritten for the block's own project,
the block is moved to the page corner (whole 2.54 mm steps, so it stays on the grid) on the smallest
of A4/A3/A2 that fits, and the title block gets --title and the licence.

--top also writes the block project's top sheet: one sheet symbol (--sheet-name, file <out>) with a
pin per port, each wired to a global label of the same name. Each --flag (a power net the block
uses but nothing in it drives, such as +3V3) gets a global label of that name and a PWR_FLAG there, so
ERC passes.

Standard library only. Exit codes: 0 written; 1 the cut isn't clean (the reason is printed); 2 bad
arguments.
"""
import argparse
import os
import re
import sys
import uuid

LICENCE = 'CERN-OHL-P-2.0'
GRID = 2.54
CORNER = 25.4
PAPERS = (('A4', 297.0, 210.0), ('A3', 420.0, 297.0), ('A2', 594.0, 420.0))
POS_RE = re.compile(r'\((at|xy|start|end|mid|center) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)')


class CutError(Exception):
    pass


# --- s-expression items, by text position (the file is never re-printed, only sliced) ---

def _children(text):
    """The items one level inside the first '(' of text: [(kind, start, end)], where start is the
    beginning of the item's line and end is just past the newline after its closing ')'."""
    out = []
    depth = 0
    i = 0
    start = None
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == '\\':
                    i += 1
                i += 1
        elif c == '(':
            depth += 1
            if depth == 2:
                start = text.rfind('\n', 0, i) + 1
                if text[start:i].strip():          # item doesn't start its line
                    start = i
                kind = re.match(r'\(([^\s()"]+)', text[i:]).group(1)
        elif c == ')':
            depth -= 1
            if depth == 1 and start is not None:
                end = i + 1
                nl = text.find('\n', end)
                if nl != -1 and not text[end:nl].strip():
                    end = nl + 1
                out.append((kind, start, end))
                start = None
            if depth == 0:
                break
        i += 1
    return out


def split_top(text):
    """(head, [(kind, chunk)], tail): the file's top-level items; head + chunks + tail == text."""
    items = _children(text)
    if not items:
        return text, [], ''
    head = text[:items[0][1]]
    chunks = []
    for k, (kind, s, e) in enumerate(items):
        nxt = items[k + 1][1] if k + 1 < len(items) else e
        chunks.append((kind, text[s:nxt]))      # anything between items rides with the item before
    return head, chunks, text[items[-1][2]:]


def _remove_child(chunk, pred):
    """chunk without the direct children for which pred(kind, text) is true."""
    parts, last = [], 0
    for kind, s, e in _children(chunk):
        if pred(kind, chunk[s:e]):
            parts.append(chunk[last:s])
            last = e
    parts.append(chunk[last:])
    return ''.join(parts)


# --- geometry ---

def _num(s):
    return float(s)


def _fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def _points(kind, chunk):
    """The points that place an item on the sheet (a wire's two ends; otherwise its first at/xy)."""
    if kind == 'wire' or kind == 'bus':
        return [(_num(a), _num(b)) for a, b in re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)', chunk)[:2]]
    m = POS_RE.search(chunk)
    return [(_num(m.group(2)), _num(m.group(3)))] if m else []


def _ref(chunk):
    m = re.search(r'\(property "Reference" "([^"]*)"', chunk)
    return m.group(1) if m else None


def _shift(chunk, dx, dy):
    return POS_RE.sub(lambda m: f'({m.group(1)} {_fmt(_num(m.group(2)) + dx)} {_fmt(_num(m.group(3)) + dy)}', chunk)


# --- the cut ---

PLACED = {'symbol', 'wire', 'bus', 'bus_entry', 'junction', 'no_connect', 'label', 'global_label',
          'hierarchical_label', 'text', 'text_box', 'polyline', 'rectangle', 'circle', 'arc', 'image',
          'sheet', 'netclass_flag', 'rule_area'}


def cut(text, keep, ports, rename, project, path, title, margin=15.0):
    head, chunks, tail = split_top(text)
    keep = set(keep)
    ports = set(ports)

    anchors, found = [], set()
    for kind, c in chunks:
        if kind == 'symbol' and _ref(c) in keep:
            found.add(_ref(c))
            anchors += _points(kind, c)
    missing = keep - found
    if missing:
        raise CutError('not on the sheet: ' + ' '.join(sorted(missing)))
    x0 = min(p[0] for p in anchors) - margin
    x1 = max(p[0] for p in anchors) + margin
    y0 = min(p[1] for p in anchors) - margin
    y1 = max(p[1] for p in anchors) + margin

    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    kept, problems, labels = [], [], set()
    for kind, c in chunks:
        if kind not in PLACED:
            kept.append((kind, c))
            continue
        pts = _points(kind, c)
        ins = [inside(p) for p in pts]
        if kind == 'symbol':
            ref = _ref(c) or '?'
            if ref in keep:
                kept.append((kind, c))
            elif ins and all(ins):
                if ref.startswith('#'):
                    kept.append((kind, c))
                else:
                    problems.append(f'{ref} is inside the block but not in --keep')
            continue
        if kind in ('wire', 'bus') and any(ins) and not all(ins):
            problems.append('a wire leaves the block at ' + ' -> '.join(f'({_fmt(x)}, {_fmt(y)})' for x, y in pts))
            continue
        if not ins or not all(ins):
            continue
        if kind == 'global_label':
            name = re.match(r'\s*\(global_label "([^"]*)"', c).group(1)
            if name not in ports:
                problems.append(f'global label {name} is inside the block but not a port (--ports)')
                continue
            labels.add(name)
            c = c.replace('(global_label ', '(hierarchical_label ', 1)
            c = _remove_child(c, lambda k, t: k == 'property' and '"Intersheetrefs"' in t)
            kind = 'hierarchical_label'
        kept.append((kind, c))
    for p in sorted(ports - labels):
        problems.append(f'port {p} has no global label inside the block')
    if problems:
        raise CutError('; '.join(problems))

    old, new = rename
    used = set()
    out = []
    for kind, c in kept:
        if old:
            c = c.replace(f'"{old}:', f'"{new}:')
        if kind == 'symbol':
            used.add(re.search(r'\(lib_id "([^"]+)"', c).group(1))
            c = re.sub(r'\(project "[^"]*"', f'(project "{project}"', c)
            c = re.sub(r'\(path "[^"]*"', f'(path "{path}"', c)
        out.append((kind, c))

    pts = [p for kind, c in out if kind in PLACED for p in _points(kind, c)]
    mx, my = min(p[0] for p in pts), min(p[1] for p in pts)
    dx = round((CORNER - mx) / GRID) * GRID
    dy = round((CORNER - my) / GRID) * GRID
    w = max(p[0] for p in pts) - mx + 2 * CORNER
    h = max(p[1] for p in pts) - my + 2 * CORNER
    paper = next((name for name, pw, ph in PAPERS if w <= pw and h <= ph), 'A1')

    result = []
    for kind, c in out:
        if kind == 'lib_symbols':
            c = _remove_child(c, lambda k, t: k == 'symbol' and re.match(r'\s*\(symbol "([^"]+)"', t).group(1) not in used)
        elif kind == 'paper':
            c = re.sub(r'\(paper "[^"]*"', f'(paper "{paper}"', c)
        elif kind == 'title_block':
            c = re.sub(r'\(title "[^"]*"\)', f'(title "{title}")', c)
            c = re.sub(r'\(comment 1 "[^"]*"\)', f'(comment 1 "{LICENCE}")', c)
            c = _remove_child(c, lambda k, t: k == 'comment' and not re.match(r'\s*\(comment 1 ', t))
        elif kind in PLACED:
            c = _shift(c, dx, dy)
        result.append(c)
    return head + ''.join(result) + tail


# --- the block project's top sheet ---

def _uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'pcb-blocks/' + '/'.join(parts)))


def _embedded(block, lib_id):
    """The embedded copy of lib_id in a schematic's lib_symbols, or ''."""
    for kind, c in split_top(block)[1]:
        if kind == 'lib_symbols':
            for k, s, e in _children(c):
                if k == 'symbol' and re.match(r'\s*\(symbol "' + re.escape(lib_id) + '"', c[s:e]):
                    return c[s:e]
    return ''


def _power_symbol(project, root_uuid, lib_id, ref, value, x, y):
    def prop(name, val, py, hide):
        h = '\n\t\t\t\t(hide yes)' if hide else ''
        return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {_fmt(x)} {_fmt(py)} 0)\n'
                f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){h}\n\t\t\t)\n\t\t)\n')
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {_fmt(x)} {_fmt(y)} 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n'
            f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n'
            f'\t\t(uuid "{_uid(project, "sym", ref)}")\n'
            + prop('Reference', ref, y + 6.35, True) + prop('Value', value, y - 3.81, False)
            + prop('Footprint', '', y, True) + prop('Datasheet', '', y, True)
            + f'\t\t(pin "1"\n\t\t\t(uuid "{_uid(project, "pin1", ref)}")\n\t\t)\n'
            f'\t\t(instances\n\t\t\t(project "{project}"\n\t\t\t\t(path "/{root_uuid}"\n'
            f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')


def make_top(project, sheet_name, sheet_file, ports, root_uuid, sheet_uuid, title, flags=(), block=''):
    """A top sheet holding one sheet symbol whose pins (one per port, in order) are each wired to a
    global label of the same name. ports: names, or (name, shape) pairs. flags: power nets (power:<name>
    symbols in the block) that nothing in the block drives; each gets a global label of its name wired
    to a PWR_FLAG, whose symbol is copied from the block's lib_symbols."""
    ports = [(p, 'passive') if isinstance(p, str) else p for p in ports]
    sx, sy, sw = 63.5, 38.1, 38.1
    sh = GRID * (len(ports) + 1)
    pins, wires, labels = [], [], []
    syms, libs = [], []
    # Each flagged net: a global label of its name (it joins the block's power symbols of that name)
    # wired to a PWR_FLAG. A PWR_FLAG wired only to a power symbol fails KiCad 10's pin_not_connected.
    for i, net in enumerate(flags):
        y = sy + sh + 20.32 + 10.16 * i
        fx = sx + 7.62
        syms.append(_power_symbol(project, root_uuid, 'power:PWR_FLAG', f'#FLG0{i + 1:02d}', 'PWR_FLAG', fx, y))
        wires.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {_fmt(sx)} {_fmt(y)}) (xy {_fmt(fx)} {_fmt(y)})\n\t\t)\n'
                     f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{_uid(project, "flagwire", net)}")\n\t)\n')
        labels.append(f'\t(global_label "{net}"\n\t\t(shape passive)\n\t\t(at {_fmt(sx)} {_fmt(y)} 180)\n'
                      f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify right)\n\t\t)\n'
                      f'\t\t(uuid "{_uid(project, "flaglabel", net)}")\n\t)\n')
    if flags:
        t = _embedded(block, 'power:PWR_FLAG')
        if not t:
            raise CutError('power:PWR_FLAG is not embedded in the block, so the top sheet cannot use it')
        libs.append(t)
    lib_text = '\t(lib_symbols)\n' if not libs else '\t(lib_symbols\n' + ''.join(libs) + '\t)\n'
    for i, (name, shape) in enumerate(ports):
        y = _fmt(sy + GRID * (i + 1))
        pins.append(f'''		(pin "{name}" {shape}
			(at {_fmt(sx)} {y} 180)
			(uuid "{_uid(project, 'pin', name)}")
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left)
			)
		)
''')
        wires.append(f'''	(wire
		(pts
			(xy {_fmt(sx - 12.7)} {y}) (xy {_fmt(sx)} {y})
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{_uid(project, 'wire', name)}")
	)
''')
        labels.append(f'''	(global_label "{name}"
		(shape {shape})
		(at {_fmt(sx - 12.7)} {y} 180)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify right)
		)
		(uuid "{_uid(project, 'label', name)}")
	)
''')
    return f'''(kicad_sch
	(version 20260306)
	(generator "pcb-blocks-cut_sheet")
	(generator_version "10.0")
	(uuid "{root_uuid}")
	(paper "A4")
	(title_block
		(title "{title}")
		(comment 1 "{LICENCE}")
	)
{lib_text}{''.join(syms)}{''.join(wires)}{''.join(labels)}	(sheet
		(at {_fmt(sx)} {_fmt(sy)})
		(size {_fmt(sw)} {_fmt(sh)})
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(stroke
			(width 0.1524)
			(type solid)
		)
		(fill
			(color 0 0 0 0.0000)
		)
		(uuid "{sheet_uuid}")
		(property "Sheetname" "{sheet_name}"
			(at {_fmt(sx)} {_fmt(sy - 0.7116)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left bottom)
			)
		)
		(property "Sheetfile" "{sheet_file}"
			(at {_fmt(sx)} {_fmt(sy + sh + 0.5846)} 0)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left top)
			)
		)
{''.join(pins)}		(instances
			(project "{project}"
				(path "/{root_uuid}"
					(page "2")
				)
			)
		)
	)
	(sheet_instances
		(path "/"
			(page "1")
		)
	)
	(embedded_fonts no)
)
'''


def _label_shapes(text):
    return {m.group(1): m.group(2) for m in re.finditer(r'\(hierarchical_label "([^"]*)"\s*\(shape (\w+)\)', text)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Cut a block out of a drawn KiCad sheet (pcb-blocks).')
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--keep', required=True, help='file with one reference per line')
    ap.add_argument('--ports', required=True, help='comma-separated global label names that become ports')
    ap.add_argument('--rename', default='', help='old=new library prefix')
    ap.add_argument('--project', required=True)
    ap.add_argument('--root-uuid', required=True)
    ap.add_argument('--sheet-uuid', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--margin', type=float, default=15.0)
    ap.add_argument('--top', default='')
    ap.add_argument('--sheet-name', default='')
    ap.add_argument('--flag', action='append', default=[],
                    help='power net the block uses but does not drive (e.g. +3V3): PWR_FLAG on the top sheet')
    a = ap.parse_args(argv)
    if a.top and not a.sheet_name:
        ap.error('--top needs --sheet-name')
    keep = [ln.strip() for ln in open(a.keep, encoding='utf-8') if ln.strip()]
    ports = [p.strip() for p in a.ports.split(',') if p.strip()]
    rename = tuple(a.rename.split('=', 1)) if a.rename else ('', '')
    text = open(a.src, encoding='utf-8', newline='').read()
    try:
        out = cut(text, keep, ports, rename, a.project, f'/{a.root_uuid}/{a.sheet_uuid}', a.title, a.margin)
    except CutError as e:
        print('The cut is not clean: ' + str(e), file=sys.stderr)
        return 1
    with open(a.out, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    print(f'wrote {a.out}')
    if a.top:
        shapes = _label_shapes(out)
        top = make_top(a.project, a.sheet_name, os.path.basename(a.out), [(p, shapes.get(p, 'passive')) for p in ports],
                       a.root_uuid, a.sheet_uuid, a.title, flags=a.flag, block=out)
        with open(a.top, 'w', encoding='utf-8', newline='') as f:
            f.write(top)
        print(f'wrote {a.top}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
