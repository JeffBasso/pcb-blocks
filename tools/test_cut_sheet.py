"""Tests for cut_sheet.py. Run from the repo root: python -m unittest discover -s tools"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut_sheet  # noqa: E402

LIB = '''	(lib_symbols
		(symbol "Device:R"
			(symbol "R_1_1"
				(pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 1.27) (name "~") (number "2"))
			)
		)
		(symbol "Device:C"
			(symbol "C_1_1")
		)
		(symbol "old:U"
			(property "Footprint" "old:FP")
		)
		(symbol "power:GND"
			(power)
		)
	)
'''


def sym(lib_id, ref, x, y, fp='Resistor_SMD:R_0603_1608Metric'):
    return f'''	(symbol
		(lib_id "{lib_id}")
		(at {x} {y} 0)
		(uuid "u-{ref}")
		(property "Reference" "{ref}"
			(at {x} {y} 0)
		)
		(property "Footprint" "{fp}"
			(at {x} {y} 0)
		)
		(instances
			(project "board"
				(path "/aaaa/bbbb"
					(reference "{ref}")
					(unit 1)
				)
			)
		)
	)
'''


def wire(x1, y1, x2, y2):
    return f'''	(wire
		(pts
			(xy {x1} {y1}) (xy {x2} {y2})
		)
		(uuid "w-{x1}-{y1}-{x2}-{y2}")
	)
'''


def sheet(*items):
    return ('(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(uuid "root")\n\t(paper "A2")\n'
            '\t(title_block\n\t\t(title "board - Power")\n\t\t(comment 1 "CERN-OHL-W-2.0")\n\t)\n'
            + LIB + ''.join(items) +
            '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n)\n')


BASE = [
    sym('Device:R', 'R1', 100, 100),
    sym('Device:R', 'R2', 110, 100),
    sym('old:U', 'U1', 105, 120, fp='old:FP'),
    sym('power:GND', '#PWR01', 110, 110, fp=''),
    sym('Device:C', 'C9', 300, 300, fp='Capacitor_SMD:C_0603_1608Metric'),
    wire(100, 96.19, 110, 96.19),
    wire(110, 103.81, 110, 110),
    wire(300, 296.19, 320, 296.19),
    '\t(junction\n\t\t(at 110 96.19)\n\t\t(diameter 0)\n\t)\n',
    '\t(junction\n\t\t(at 320 296.19)\n\t\t(diameter 0)\n\t)\n',
    '\t(global_label "IN"\n\t\t(shape input)\n\t\t(at 100 96.19 180)\n\t\t(fields_autoplaced yes)\n'
    '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify right)\n\t\t)\n\t\t(uuid "g-in")\n'
    '\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at 90 96.19 0)\n\t\t\t(hide yes)\n\t\t)\n\t)\n',
    '\t(label "MID"\n\t\t(at 105 96.19 0)\n\t\t(uuid "l-mid")\n\t)\n',
    '\t(text "Block heading"\n\t\t(at 95 90 0)\n\t\t(uuid "t1")\n\t)\n',
    '\t(text "Far away note"\n\t\t(at 300 320 0)\n\t\t(uuid "t2")\n\t)\n',
]

KEEP = {'R1', 'R2', 'U1'}


def run(items=None, **kw):
    args = dict(keep=KEEP, ports={'IN'}, rename=('old', 'pcb-blocks'), project='blk',
                path='/rrrr/ssss', title='pcb-blocks - Test', margin=15.0)
    args.update(kw)
    return cut_sheet.cut(sheet(*(items if items is not None else BASE)), **args)


class SplitTest(unittest.TestCase):
    def test_round_trip_is_exact(self):
        text = sheet(*BASE)
        head, chunks, tail = cut_sheet.split_top(text)
        self.assertEqual(head + ''.join(c for _, c in chunks) + tail, text)

    def test_chunk_kinds(self):
        _, chunks, _ = cut_sheet.split_top(sheet(*BASE))
        kinds = [k for k, _ in chunks]
        self.assertEqual(kinds.count('symbol'), 5)
        self.assertEqual(kinds.count('wire'), 3)
        self.assertIn('lib_symbols', kinds)


class CutTest(unittest.TestCase):
    def test_keeps_listed_parts_and_power_symbols_inside(self):
        out = run()
        for ref in ('R1', 'R2', 'U1', '#PWR01'):
            self.assertIn(f'(property "Reference" "{ref}"', out)
        self.assertNotIn('"C9"', out)

    def test_drops_wires_junctions_and_text_outside_the_block(self):
        out = run()
        self.assertEqual(len(re.findall(r'^\t\(wire', out, re.M)), 2)
        self.assertEqual(len(re.findall(r'^\t\(junction', out, re.M)), 1)
        self.assertIn('Block heading', out)
        self.assertNotIn('Far away note', out)

    def test_port_global_label_becomes_hierarchical(self):
        out = run()
        self.assertIn('(hierarchical_label "IN"', out)
        self.assertNotIn('(global_label', out)
        self.assertNotIn('Intersheetrefs', out)

    def test_global_label_that_is_not_a_port_fails(self):
        with self.assertRaises(cut_sheet.CutError):
            run(ports=set())

    def test_listed_part_missing_fails(self):
        with self.assertRaises(cut_sheet.CutError):
            run(keep=KEEP | {'R77'})

    def test_unlisted_part_inside_the_block_fails(self):
        with self.assertRaises(cut_sheet.CutError) as e:
            run(items=BASE + [sym('Device:R', 'R5', 104, 104)])
        self.assertIn('R5', str(e.exception))

    def test_wire_leaving_the_block_fails(self):
        with self.assertRaises(cut_sheet.CutError):
            run(items=BASE + [wire(110, 110, 110, 250)])

    def test_rename_lib_ids_embedded_symbols_and_footprints(self):
        out = run()
        self.assertIn('(lib_id "pcb-blocks:U")', out)
        self.assertIn('(symbol "pcb-blocks:U"', out)
        self.assertIn('"pcb-blocks:FP"', out)
        self.assertNotIn('"old:', out)

    def test_drops_unused_embedded_symbols(self):
        out = run()
        self.assertNotIn('(symbol "Device:C"', out)
        self.assertIn('(symbol "Device:R"', out)
        self.assertIn('(symbol "power:GND"', out)

    def test_rewrites_instances_and_title(self):
        out = run()
        self.assertIn('(project "blk"', out)
        self.assertIn('(path "/rrrr/ssss"', out)
        self.assertNotIn('(project "board"', out)
        self.assertIn('(title "pcb-blocks - Test")', out)
        self.assertIn('(comment 1 "CERN-OHL-P-2.0")', out)

    def test_moves_the_block_to_the_page_corner_on_the_grid(self):
        out = run()
        # R1 was at 100,100; the block moves toward the page corner by a whole number of 2.54 mm steps.
        m = re.search(r'\(lib_id "Device:R"\)\n\t\t\(at (-?[\d.]+) (-?[\d.]+)', out)
        x, y = float(m.group(1)), float(m.group(2))
        self.assertAlmostEqual(round((x - 100) / 2.54) * 2.54, x - 100, places=6)
        self.assertAlmostEqual(round((y - 100) / 2.54) * 2.54, y - 100, places=6)
        self.assertLess(x, 100)
        self.assertIn('(paper "A4")', out)
        # Symbol-local coordinates inside lib_symbols are not moved.
        self.assertIn('(at 0 3.81 270)', out)


class TopTest(unittest.TestCase):
    def test_top_sheet_has_one_sheet_with_a_pin_and_global_label_per_port(self):
        top = cut_sheet.make_top(project='blk', sheet_name='PoE PD', sheet_file='blk_sheet.kicad_sch',
                                 ports=['A', 'B'], root_uuid='rrrr', sheet_uuid='ssss', title='pcb-blocks - X')
        self.assertIn('(property "Sheetname" "PoE PD"', top)
        self.assertIn('(property "Sheetfile" "blk_sheet.kicad_sch"', top)
        self.assertEqual(len(re.findall(r'\(pin "(A|B)" ', top)), 2)
        self.assertEqual(len(re.findall(r'\(global_label "(A|B)"', top)), 2)
        self.assertEqual(len(re.findall(r'^\t\(wire', top, re.M)), 2)
        self.assertIn('(path "/rrrr"', top)
        _, chunks, _ = cut_sheet.split_top(top)
        self.assertTrue(chunks)

    def test_flags_a_power_net_through_a_global_label_of_its_name(self):
        # A PWR_FLAG wired only to a power symbol fails KiCad 10's pin_not_connected check; wired to a
        # global label of the same name it joins the block's power symbols and ERC has 0 errors.
        block = ('(kicad_sch\n\t(lib_symbols\n\t\t(symbol "power:+3V3"\n\t\t\t(power)\n\t\t)\n'
                 '\t\t(symbol "power:PWR_FLAG"\n\t\t\t(power)\n\t\t)\n\t)\n)\n')
        top = cut_sheet.make_top(project='blk', sheet_name='S', sheet_file='s.kicad_sch', ports=['A'],
                                 root_uuid='rrrr', sheet_uuid='ssss', title='t', flags=['+3V3'], block=block)
        self.assertIn('(symbol "power:PWR_FLAG"', top)
        self.assertIn('(lib_id "power:PWR_FLAG")', top)
        self.assertNotIn('(lib_id "power:+3V3")', top)
        self.assertIn('(global_label "+3V3"', top)
        self.assertIn('(path "/rrrr"', top)
        self.assertEqual(len(re.findall(r'^\t\(wire', top, re.M)), 2)

    def test_flag_without_an_embedded_pwr_flag_fails(self):
        with self.assertRaises(cut_sheet.CutError):
            cut_sheet.make_top(project='blk', sheet_name='S', sheet_file='s.kicad_sch', ports=['A'],
                               root_uuid='rrrr', sheet_uuid='ssss', title='t', flags=['GND'], block='(kicad_sch\n)\n')


if __name__ == '__main__':
    unittest.main()
