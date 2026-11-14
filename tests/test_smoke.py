import math
import unittest
import pykalos

class SmokeTest(unittest.TestCase):
    def test_core_call(self):
        left = [1.0, -0.4]
        self.assertEqual(pykalos.convolve(left, [1.0, 0.2]), [1.0, -0.2, -0.08000000000000002])
        self.assertEqual(left, [1.0, -0.4])

    def test_validation_and_reuse(self):
        for left in [[], [math.inf], [math.nan]]:
            with self.assertRaises(ValueError):
                pykalos.convolve(left, [1.0])
        self.assertEqual(pykalos.convolve([2.0], [3.0]), [6.0])

    def test_metadata(self):
        info = pykalos.core_version()
        self.assertRegex(info["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(info["provider"], "OpenBLAS")
        self.assertEqual(info["blas_integer_bits"], 32)
        self.assertFalse(pykalos.capabilities()["fit"])

if __name__ == "__main__":
    unittest.main()
