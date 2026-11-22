"""Tests for poe_pd_90w.py (run: python -I -m unittest discover -s blocks/poe_pd/calc)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poe_pd_90w as c  # noqa: E402


class Case(unittest.TestCase):
    def test_current_at_90w_from_52v(self):
        self.assertAlmostEqual(c.i_load(90.0, 52.0), 1.7308, places=3)

    def test_fet_loss_is_i_squared_r(self):
        # 1.73 A through 192 mohm (PSMN075 175 C max) = 0.575 W
        self.assertAlmostEqual(c.fet_loss(1.7308, 0.192), 0.5752, places=3)

    def test_max_rth_for_tj(self):
        # (125 - 50) / 0.575 W = 130 K/W
        self.assertAlmostEqual(c.rth_max(0.5752, 50.0, 125.0), 130.4, places=0)


class Bridge(unittest.TestCase):
    def test_psmn040_loss_at_50v(self):
        # 1.80 A x 98.8 mohm (36.6 x 2.7) = 0.320 W
        self.assertAlmostEqual(c.fet_loss(90.0 / 50.0, 0.0366 * 2.7), 0.320, places=3)

    def test_lt4321_drop_window(self):
        # LT4321 p8: VF = IAVG x Rds(on) in 20-70 mV; 1.80 A x 36.6 mohm = 65.9 mV
        self.assertAlmostEqual(c.fet_drop(1.80, 0.0366) * 1e3, 65.9, places=1)


class Leakage(unittest.TestCase):
    def test_idss_endpoints(self):
        # PSMN040 p5: IDSS max 1 uA at 25 C, 500 uA at 175 C (VDS 100 V)
        self.assertAlmostEqual(c.idss_at(25.0), 1e-6, places=12)
        self.assertAlmostEqual(c.idss_at(175.0), 500e-6, places=10)

    def test_idss_at_50c(self):
        self.assertAlmostEqual(c.idss_at(50.0) * 1e6, 2.82, places=2)

    def test_slope_sqrt_law(self):
        # I = I100 sqrt(V / 100): dI/dV = I / (2 V); at 100 V with 1 uA: 5 nA/V per FET
        self.assertAlmostEqual(c.leak_slope(1e-6, 100.0, 1), 5e-9, places=15)

    def test_signature_unchanged_without_leakage(self):
        self.assertAlmostEqual(c.parallel_sig(24.4e3, 0.0), 24.4e3)
        self.assertLess(c.parallel_sig(24.4e3, 1e-6), 24.4e3)


class Inrush(unittest.TestCase):
    def test_lt4294_example(self):
        # LT4294 p8: IINRUSH = IGPU * CPORT / CGATE; 22 uA, 22 uF, 47 nF -> ~10 mA
        self.assertAlmostEqual(c.inrush(22e-6, 22e-6, 47e-9), 0.0103, places=4)

    def test_bounds_order(self):
        lo, hi = c.inrush_bounds(cport=100e-6, cgate=47e-9)
        self.assertLess(lo, hi)
        self.assertLess(hi, 0.350)


class Cpd(unittest.TestCase):
    def test_window(self):
        lo, hi = c.cpd_bounds([(47e-9, 0.10), (47e-9, 0.10), (1e-9, 0.10), (1e-9, 0.10)])
        self.assertAlmostEqual(lo, 0.0864e-6, places=10)
        self.assertAlmostEqual(hi, 0.1056e-6, places=10)


class Opto(unittest.TestCase):
    def test_led_current_range(self):
        lo, hi = c.led_current(33e3, 0.01, (37.0, 57.0), vf=(1.0, 1.4), vol=(0.0, 0.8))
        self.assertAlmostEqual(lo * 1e3, 1.04, places=2)
        self.assertAlmostEqual(hi * 1e3, 1.71, places=2)

    def test_resistor_power(self):
        self.assertAlmostEqual(c.r_power(56.0, 33e3 * 0.99), 0.0960, places=3)


if __name__ == '__main__':
    unittest.main()
