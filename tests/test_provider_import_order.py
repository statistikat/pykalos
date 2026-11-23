"""Exercise both numerical libraries in fresh processes for each import order."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

EVIDENCE = Path(__file__).resolve().parents[1] / "vendor/kalos-evidence/native/tramo-transform"


def numpy_probe(np):
    # Nontrivial LAPACK work through NumPy's own linked implementation.
    solution = np.linalg.solve([[3., 1.], [1., 2.]], [7., 4.])
    np.testing.assert_allclose(solution, [2., 1.], rtol=1e-14, atol=0)
    return solution.tolist()


def kalos_probe(package):
    with (EVIDENCE / "inputs.csv").open(newline="") as stream:
        line = next(r["line"] for r in csv.DictReader(stream)
                    if r["id"] == "tr_gs" and r["line"].startswith("values "))
    with (EVIDENCE / "transform-facts.csv").open(newline="") as stream:
        facts = {r["key"]: r["value"] for r in csv.DictReader(stream) if r["id"] == "tr_gs"}
    fields = facts["in"].split()
    request = dict(zip(fields[::2], fields[1::2]))
    result = package.tramo_transform_decision(
        [float(v) for v in line.split()[1:]], float(request["logpref"]), float(request["prec"]))
    for key in ("level_ll", "log_ll", "log_correction"):
        if result[key].hex() != float(facts[key]).hex():
            raise ValueError(f"{key} disagrees with the frozen TRAMO readout")
    if result["loglevel_status"] != facts["loglevel_status"]:
        raise ValueError("TRAMO log/level choice disagrees with the capture")
    return package.core_version()


def exercise(first):
    if first == "numpy":
        import numpy as np
        before = numpy_probe(np)
        import pykalos
        after = numpy_probe(np)
    else:
        import pykalos
        before = kalos_probe(pykalos)
        import numpy as np
        after = kalos_probe(pykalos)
    if before != after:
        raise RuntimeError(f"{first} results changed after loading the second library")
    print(json.dumps({"numpy": numpy_probe(np), "kalos": kalos_probe(pykalos)}, sort_keys=True))


class ImportOrderTest(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is optional")
    def test_lapack_in_both_orders(self):
        results = []
        for first in ("numpy", "pykalos"):
            run = subprocess.run([sys.executable, __file__, first], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, f"{first} imported first: {run.stderr}")
            results.append(json.loads(run.stdout))
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    if sys.argv[1:] in (["numpy"], ["pykalos"]):
        exercise(sys.argv[1])
    else:
        unittest.main()
