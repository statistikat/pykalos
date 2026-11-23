"""Qualify the Python restricted fit against both immutable JVM corpora."""
from collections import defaultdict
import csv
import math
import struct
from pathlib import Path
import unittest

import pykalos
from x13auto_corpus import verify_sha256sums

EVIDENCE = Path(__file__).resolve().parents[1] / "vendor/kalos-evidence/native"
MODES = {"Additive": "additive", "Multiplicative": "multiplicative",
         "LogAdditive": "log_additive", "PseudoAdditive": "pseudo_additive"}
CLASSES = {"days": "days_related", "holiday": "moving_holiday", "user": "user", "outlier": "outlier"}
EFFECTS = {"Undefined": "undefined", "Series": "series", "Trend": "trend", "Seasonal": "seasonal",
           "SeasonallyAdjusted": "seasonally_adjusted", "Irregular": "irregular", "CalendarEffect": "calendar_effect"}


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def indexed_values(rows):
    return [float(row["value"]) for row in sorted(rows, key=lambda r: int(r["row"]))]


def load_cases(dirname):
    path = EVIDENCE / dirname
    verify_sha256sums(path)
    inputs = defaultdict(list)
    variables = defaultdict(lambda: defaultdict(list))
    columns = defaultdict(lambda: defaultdict(list))
    tables = defaultdict(lambda: defaultdict(list))
    for row in read(path / "inputs.csv"):
        inputs[row["case"]].append(row)
    for row in read(path / "vars.csv"):
        variables[row["case"]][int(row["index"])].append(row)
    for row in read(path / "columns.csv"):
        columns[row["case"], int(row["index"])][int(row["coef"])].append(row)
    for row in read(path / "tables.csv"):
        tables[row["case"]][row["table"]].append(row)
    for case in read(path / "cases.csv"):
        cid = case["case"]
        vars_ = []
        for idx, records in sorted(variables[cid].items()):
            vars_.append({"class": CLASSES[records[0]["class"]], "effect": EFFECTS[records[0]["effect"]],
                          "coefficient": [float(r["coefficient"]) for r in records],
                          "columns": [indexed_values(col) for _, col in sorted(columns[cid, idx].items())]})
        freq = int(case["frequency"])
        filters = case["filters"].split(",") if "filters" in case else ["9"] * freq
        spec = dict(variables=vars_, frequency=freq, start_period=int(case["first_period"]),
                    log=case["log"] == "TRUE", mode=MODES[case["mode_requested"]],
                    seasonal=["stable" if f == "0" else "s3x" + f for f in filters],
                    trend_length=int(case.get("henderson", 5)), lower_sigma=float(case.get("lower", 1.5)),
                    upper_sigma=float(case.get("upper", 2.5)), backcast=int(case.get("backcast", 0)),
                    forecast=int(case.get("forecast", 0)))
        yield case, indexed_values(inputs[cid]), spec, {k: indexed_values(rows) for k, rows in tables[cid].items()}


class FixedFitTest(unittest.TestCase):
    def test_reference_corpora(self):
        completed = refused = 0
        for dirname in ("x13-allocation", "x13-fit"):
            for case, series, spec, expected in load_cases(dirname):
                with self.subTest(case=case["case"]):
                    result = pykalos.x13_fit(series, **spec)
                    for key in ("frequency", "start_period", "seasonal", "trend_length", "backcast",
                                "forecast", "log", "lower_sigma", "upper_sigma"):
                        self.assertEqual(result[key], spec[key])
                    self.assertEqual(result["mode_requested"], spec["mode"])
                    self.assertEqual(result["mode_effective"], MODES[case["mode_effective"]])
                    self.assertEqual(result["sigma_policy_provenance"], "legacy (default)")
                    if case.get("route") == "arima":
                        self.assertEqual(result["status"], "unsupported:x13 fit requires zero horizons")
                        self.assertFalse(result["available"])
                        self.assertNotIn("finals", result)
                        refused += 1
                        continue
                    completed += 1
                    self.assertEqual(result["status"], "available")
                    self.assertTrue(result["available"])
                    self.assertEqual(result["selection"]["status"], "available")
                    self.assertEqual(result["selection"]["trend_length"], spec["trend_length"])
                    actual = {**result["preadjustment"], **result["results"], **result["finals"]}
                    self.assertEqual(len(expected), 27)
                    self.assertEqual(set(actual), set(expected))
                    for table, reference in expected.items():
                        values = actual[table]
                        self.assertEqual(len(values), len(reference))
                        # Kalos's fixed-fit contract: log preadjustment crosses exp,
                        # followed by X-11 and then the restore. a1 is always exact.
                        if not spec["log"] or table == "a1":
                            self.assertEqual(struct.pack(f">{len(values)}d", *values),
                                             struct.pack(f">{len(reference)}d", *reference), table)
                        else:
                            band = (1e-15 if table in result["preadjustment"] else
                                    1e-12 if table in result["results"] else 1e-9)
                            self.assertTrue(all(math.isfinite(x) for x in values), table)
                            worst = max(abs(a - b) / (abs(b) if b else 1.) for a, b in zip(values, reference))
                            self.assertLessEqual(worst, band, table)
                    for name, key in (("finalSA", "d11final"), ("finalTrend", "d12final"),
                                      ("finalIrregular", "d13final")):
                        self.assertEqual(result[name], result["finals"][key])
                    if case.get("x13fast") == "TRUE":
                        fast = defaultdict(list)
                        for row in read(EVIDENCE / dirname / "x13fast.csv"):
                            fast[row["table"]].append(row)
                        self.assertEqual(len(fast), 14)
                        for table, rows in fast.items():
                            self.assertEqual(actual[table], indexed_values(rows), table)
        self.assertEqual((completed, refused), (16, 2))

    def test_refusals_and_boundary(self):
        case, values, spec, _ = next(load_cases("x13-allocation"))
        cap = pykalos.capabilities()
        self.assertTrue(cap["restricted_fit"]["qualified"])
        self.assertEqual(cap["restricted_fit"]["qualified_frequencies"], (4, 12))
        self.assertFalse(cap["fit"])
        for patch, message in (({"trend_length": 0}, "fixed Henderson trend length"),
                               ({"seasonal": ["msr"] * 4}, "fixed seasonal requests only"),
                               ({"forecast": -1}, "requires zero horizons")):
            with self.subTest(**patch):
                result = pykalos.x13_fit(values, **{**spec, **patch})
                self.assertEqual(result["status"], "unsupported:x13 fit " + message)
                self.assertNotIn("results", result)
        for patch in ({"seasonal": "s3x9"}, {"seasonal": ["typo"] * 4}, {"seasonal": ["stable"]},
                      {"trend_length": 4}, {"trend_length": 5.5}, {"log": "False"}, {"start_period": 2**31},
                      {"variables": [{}]}, {"variables": [{"class": "user", "effect": "trend",
                                                        "coefficient": [1.], "columns": [[0.]]}]},
                      {"mode": "unknown"}, {"sigma": "unknown"}, {"msr_policy": "unknown"}):
            with self.subTest(**patch), self.assertRaises((ValueError, TypeError)):
                pykalos.x13_fit(values, **{**spec, **patch})
        for bad in ("123", [False] * len(values), [[2.]] * 96, [float("nan")] * 96):
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                pykalos.x13_fit(bad, **spec)
        copy = list(values)
        legacy = pykalos.x13_fit(values, **spec, sigma="legacy")
        accurate = pykalos.x13_fit(values, **spec, sigma="accurate")
        self.assertEqual(values, copy)
        self.assertEqual(legacy["sigma_policy_provenance"], "legacy (explicit)")
        self.assertEqual(accurate["sigma_policy_provenance"], "accurate (explicit)")
        self.assertTrue(accurate["available"])
