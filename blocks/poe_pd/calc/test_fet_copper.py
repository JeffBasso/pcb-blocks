"""Tests for fet_copper.py (run: python -I -m unittest discover -s blocks/poe_pd/calc)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fet_copper as f  # noqa: E402


class Curves(unittest.TestCase):
    def test_fig25_point(self):
        # Fig. 25, 0.5 W, 10 mm square: 98.5 C from 20 C -> (98.5 - 20) / 0.5 = 157 K/W
        self.assertAlmostEqual(f.rth_stack(10.0, 0.5, 70), 157.0, places=1)

    def test_fig35_point(self):
        # Fig. 35 (4 x 2 oz), 0.5 W, 10 mm: 83.5 C -> 127 K/W
        self.assertAlmostEqual(f.rth_stack(10.0, 0.5, 280), 127.0, places=1)

    def test_more_copper_is_cooler(self):
        self.assertLess(f.rth_stack(9.0, 0.32, 140), f.rth_stack(9.0, 0.32, 70))
        self.assertLess(f.rth_stack(12.0, 0.32, 140), f.rth_stack(9.0, 0.32, 140))

    def test_below_70um_uses_the_fin_model_and_is_hotter(self):
        self.assertGreater(f.rth_stack(12.0, 0.5, 35), f.rth_stack(12.0, 0.5, 70))


class Case(unittest.TestCase):
    def test_issue15_table_psmn040_4l(self):
        # Ion-Speakers#15 comparison: PSMN040 at 0.320 W, 4 x 1 oz, 9.0 mm square -> ~107 C; 114 C with no inner credit
        self.assertAlmostEqual(f.tj(9.0, 0.320, 140), 107.0, delta=1.0)
        self.assertAlmostEqual(f.tj(9.0, 0.320, 70), 114.0, delta=1.0)

    def test_effective_side_is_sqrt_area(self):
        self.assertAlmostEqual(f.side(81.0), 9.0)


if __name__ == '__main__':
    unittest.main()
