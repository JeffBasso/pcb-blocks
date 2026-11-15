"""Tests for block_layout.py. Run from the repo root: python -m unittest discover -s tools"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_layout  # noqa: E402

PCB = '''(kicad_pcb
\t(version 20260206)
\t(generator "pcbnew")
\t(footprint "Resistor_SMD:R_0603_1608Metric"
\t\t(layer "F.Cu")
\t\t(at 100 100)
\t\t(property "Reference" "R100")
\t)
\t(gr_line
\t\t(start 97.5 99.5)
\t\t(end 159.5 99.5)
\t\t(stroke
\t\t\t(width 0.1)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "a")
\t)
\t(gr_line
\t\t(start 0 0)
\t\t(end 1 1)
\t\t(stroke
\t\t\t(width 0.1)
\t\t\t(type default)
\t\t)
\t\t(layer "F.SilkS")
\t\t(uuid "b")
\t)
\t(segment
\t\t(start 1 1)
\t\t(end 2 2)
\t\t(width 0.25)
\t\t(layer "F.Cu")
\t\t(net 1)
\t\t(uuid "c")
\t)
)
'''


class StripEdgeCuts(unittest.TestCase):
    def test_removes_only_edge_cuts_drawings(self):
        out = block_layout.strip_edge_cuts(PCB)
        self.assertNotIn('Edge.Cuts', out)
        self.assertIn('(layer "F.SilkS")', out)       # other drawings stay
        self.assertIn('(segment', out)                 # copper stays
        self.assertIn('"R100"', out)                   # footprints stay

    def test_nothing_else_changes(self):
        out = block_layout.strip_edge_cuts(PCB)
        self.assertEqual(out, PCB.replace(PCB[PCB.index('\t(gr_line\n\t\t(start 97.5'):PCB.index('\t(gr_line\n\t\t(start 0 0)')], ''))

    def test_crlf_input(self):
        out = block_layout.strip_edge_cuts(PCB.replace('\n', '\r\n'))
        self.assertNotIn('Edge.Cuts', out)


class CopyAndCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, 'blocks', 'blk'))
        os.makedirs(os.path.join(self.root, 'pcb-blocks.kicad_blocks', 'blk.kicad_block'))
        with open(os.path.join(self.root, 'blocks', 'blk', 'blk.kicad_pcb'), 'w', newline='') as f:
            f.write(PCB)

    def tearDown(self):
        self.tmp.cleanup()

    def dest(self):
        return os.path.join(self.root, 'pcb-blocks.kicad_blocks', 'blk.kicad_block', 'blk.kicad_pcb')

    def test_copy_then_check_passes(self):
        block_layout.copy(self.root, 'blk')
        self.assertTrue(os.path.exists(self.dest()))
        self.assertEqual(block_layout.check(self.root, 'blk'), [])

    def test_check_fails_when_missing(self):
        problems = block_layout.check(self.root, 'blk')
        self.assertEqual(len(problems), 1)
        self.assertIn('no layout in the design block', problems[0])

    def test_check_fails_when_layout_changed(self):
        block_layout.copy(self.root, 'blk')
        with open(os.path.join(self.root, 'blocks', 'blk', 'blk.kicad_pcb'), 'w', newline='') as f:
            f.write(PCB.replace('(width 0.25)', '(width 0.3)'))
        problems = block_layout.check(self.root, 'blk')
        self.assertEqual(len(problems), 1)
        self.assertIn('differs from blocks', problems[0])

    def test_check_fails_on_stray_layout_without_project_board(self):
        block_layout.copy(self.root, 'blk')
        os.remove(os.path.join(self.root, 'blocks', 'blk', 'blk.kicad_pcb'))
        problems = block_layout.check(self.root, 'blk')
        self.assertEqual(len(problems), 1)
        self.assertIn('has no blocks', problems[0])

    def test_no_layout_anywhere_is_fine(self):
        os.remove(os.path.join(self.root, 'blocks', 'blk', 'blk.kicad_pcb'))
        self.assertEqual(block_layout.check(self.root, 'blk'), [])


if __name__ == '__main__':
    unittest.main()
