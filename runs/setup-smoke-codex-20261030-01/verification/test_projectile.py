"""Independent QA: closed forms, physical invariants and API boundaries."""
import importlib.util
import math
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'fixture_under_review', Path(__file__).resolve().parents[1] / 'fixture/projectile.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
summary = MODULE.projectile_summary
KEYS = {'flight_time_s', 'range_m', 'max_height_m'}


class ProjectileQA(unittest.TestCase):
    def close(self, actual, expected):
        self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                        (actual, expected))

    def test_closed_forms(self):
        # 30 degrees: vy=10, vx=10 sqrt(3), derived without fixture helpers.
        cases = [(20, 30, (20/9.81, 200*math.sqrt(3)/9.81, 50/9.81)),
                 (10, 45, (10*math.sqrt(2)/9.81, 100/9.81, 25/9.81)),
                 (50, 90, (100/9.81, 0, 2500/19.62))]
        for v, a, expected in cases:
            with self.subTest(v=v, a=a):
                result = summary(v, a)
                for key, value in zip(('flight_time_s', 'range_m', 'max_height_m'), expected):
                    self.close(result[key], value)

    def test_exact_endpoints_and_positive_zero(self):
        for args in [(0, 0), (0, 90), (0, 42), (50, 0), (-0.0, -0.0)]:
            for value in summary(*args).values():
                self.assertEqual(value, 0.0)
                self.assertEqual(math.copysign(1, value), 1)
        self.assertEqual(summary(50, 90)['range_m'], 0.0)

    def test_grid_api_and_physical_invariants(self):
        for v in (0, 0.001, 1, 20, 49.999, 50):
            for a in (0, 0.001, 15, 30, 45, 60, 89.999, 90):
                with self.subTest(v=v, a=a):
                    r = summary(v, a)
                    self.assertEqual(set(r), KEYS)
                    for value in r.values():
                        self.assertIs(type(value), float)
                        self.assertTrue(math.isfinite(value) and value >= 0)
                    # Ballistic apex falls for half the flight: H = g T² / 8.
                    self.close(r['max_height_m'], 9.81*r['flight_time_s']**2/8)
                    self.assertLessEqual(r['range_m'], v*v/9.81 + 1e-12)
                    self.close(r['range_m'], summary(v, 90-a)['range_m'])

    def test_speed_scaling(self):
        for angle in (0, 13, 30, 45, 72, 90):
            small, large = summary(10, angle), summary(30, angle)
            for key, factor in [('flight_time_s', 3), ('range_m', 9), ('max_height_m', 9)]:
                self.close(large[key], factor*small[key])

    def test_near_endpoints_are_not_snapped(self):
        for angle in (math.nextafter(0.0, 1.0), 1e-8,
                      90-1e-8, math.nextafter(90.0, 0.0)):
            r = summary(50, angle)
            self.assertTrue(all(math.isfinite(x) for x in r.values()))
            # Subnormal angles can underflow legitimately; normal near-ends cannot.
            if angle > 1e-300:
                self.assertGreater(r['range_m'], 0)
                self.assertGreater(r['flight_time_s'], 0)
                self.assertGreater(r['max_height_m'], 0)

    def test_invalid_types_and_explanatory_errors(self):
        class IntSubclass(int): pass
        class FloatSubclass(float): pass
        invalid = [True, False, None, '20', 1j, [], {}, (), object(),
                   Decimal('1'), Fraction(1, 2), IntSubclass(1), FloatSubclass(1)]
        for index, name, upper in ((0, 'speed_m_s', 50), (1, 'angle_deg', 90)):
            for value in invalid:
                with self.subTest(parameter=name, value=repr(value)):
                    args = [0, 0]  # Must validate before zero-flight shortcut.
                    args[index] = value
                    with self.assertRaises(TypeError) as raised:
                        summary(*args)
                    self.assertIn(name, str(raised.exception))
                    self.assertIn(f'[0, {upper}]', str(raised.exception))

    def test_invalid_numbers_including_huge_ints(self):
        for index, name, upper in ((0, 'speed_m_s', 50), (1, 'angle_deg', 90)):
            invalid = [math.nan, math.inf, -math.inf, -1, upper+1,
                       math.nextafter(0.0, -math.inf), math.nextafter(float(upper), math.inf),
                       10**1000, -(10**1000)]
            for value in invalid:
                with self.subTest(parameter=name, value=repr(value)):
                    args = [0, 0]
                    args[index] = value
                    with self.assertRaises(ValueError) as raised:
                        summary(*args)
                    self.assertIn(name, str(raised.exception))
                    self.assertIn(f'[0, {upper}]', str(raised.exception))

    def test_fresh_dictionary(self):
        first = summary(20, 30)
        first['range_m'] = -1
        second = summary(20, 30)
        self.assertIsNot(first, second)
        self.assertGreater(second['range_m'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
