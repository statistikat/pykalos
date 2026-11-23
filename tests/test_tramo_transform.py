"""Replay the pinned 23-B pre-stage at the Python boundary, including refusals."""
import csv
import math
from pathlib import Path
import struct
import unittest

import pykalos
from x13auto_corpus import verify_sha256sums

EVIDENCE = Path(__file__).resolve().parents[1] / "vendor/kalos-evidence/native/tramo-transform"


def rows(name):
    with (EVIDENCE / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


class TramoTransformTest(unittest.TestCase):
    def assert_binary64(self, actual, captured):
        expected = float(captured)
        if math.isnan(expected):
            self.assertTrue(math.isnan(actual))
        else:
            self.assertEqual(struct.pack(">d", actual), struct.pack(">d", expected))

    def test_frozen_corpus(self):
        verify_sha256sums(EVIDENCE)
        cases = rows("cases.csv")
        self.assertEqual(len(cases), 29)
        facts = {}
        for row in rows("transform-facts.csv"):
            facts.setdefault(row["id"], {})[row["key"]] = row["value"]
        series = {r["id"]: [float(v) for v in r["line"].split()[1:]]
                  for r in rows("inputs.csv") if r["line"].startswith("values ")}
        for case in cases:
            cid = case["id"]
            with self.subTest(case=cid):
                fact = facts[cid]
                if case["kind"] == "calccv":
                    _, n, _, expected = fact["calccv"].split()
                    self.assert_binary64(pykalos.tramo_critical_value(int(n)), expected)
                    continue
                if case["kind"] == "season":
                    result = pykalos.tramo_seasonality(series[cid])
                    self.check_seasonality(result, fact)
                    continue

                fields = fact["in"].split()
                request = dict(zip(fields[::2], fields[1::2]))
                args = dict(frequency=int(request["freq"]), mean=request["mean"] == "1",
                            detect_seasonality=request["detect"] == "1",
                            spec_seasonality=request["specseas"] == "1",
                            robust=request["robust"] == "1", precision=float(request["prec"]),
                            log_preference=float(request["logpref"]))
                if args["robust"]:
                    with self.assertRaisesRegex(ValueError, "robust AO/LS"):
                        pykalos.tramo_transform_decision(series[cid], **args)
                    continue
                result = pykalos.tramo_transform_decision(series[cid], **args)
                for key in ("spec_pre", "loglevel_status"):
                    self.assertEqual(result[key], fact[key])
                for key in ("choosing_log", "log_transform", "seasonal"):
                    self.assertIs(result[key], fact[key] == "1")
                for key in ("log_ll", "level_ll", "log_correction"):
                    self.assert_binary64(result[key], fact[key])
                self.assert_binary64(result["log_preference"], fact["log_pref"])
                self.assertIs(result["nonpositive"], any(v <= 0 for v in series[cid]))
                if args["detect_seasonality"]:
                    detector = result["seasonality"]
                    self.assertEqual(f"{detector['verdict']} {detector['to_int']}", fact["season_verdict"])
                    for key, source in (("qs", "qs"), ("friedman", "np")):
                        value, p_value = fact[source].split()
                        self.assert_binary64(detector[key]["value"], value)
                        self.assert_binary64(detector[key]["p_value"], p_value)
                else:
                    self.assertIsNone(result["seasonality"])
                if cid == "tr_neg":
                    self.assertEqual(result["remarks"], ["No identifiable seasonality",
                                                         "negative values, levels are chosen"])

    def check_seasonality(self, result, fact):
        self.assertEqual(f"{result['verdict']} {result['to_int']}", fact["season_verdict"])
        for key, source in (("qs", "qs"), ("friedman", "np")):
            self.assert_binary64(result[key]["value"], fact[source + "_val"])
            self.assert_binary64(result[key]["p_value"], fact[source + "_p"])
            self.assertIs(result[key]["valid"], fact[source + "_valid"] == "true")
        _, count, *values = fact["diff"].split()
        self.assertEqual(len(result["differenced"]), int(count))
        self.assertEqual(len(values), int(count))
        for actual, captured in zip(result["differenced"], values):
            self.assert_binary64(actual, captured)

    def test_scope_and_refusals(self):
        caps = pykalos.capabilities()
        self.assertFalse(caps["fit"])
        self.assertEqual(caps["primitives"], ("convolve", "x13_automatic", "x13_fit", "tramo_critical_value",
                                              "tramo_seasonality", "tramo_transform_decision",
                                              "seats_extract_wk", "seats_from_tramo", "tramoseats_fit",
                                              "prepare_regression", "prepare_series", "estimate_sarima_fixed"))
        for count in (True, -1, 2**31, 12.5, "50"):
            with self.subTest(observations=count), self.assertRaises((ValueError, TypeError)):
                pykalos.tramo_critical_value(count)
        for series in ([1.] * 23, [0.] * 23 + [math.nan], [math.inf] * 24,
                       [[1.]] * 24, {1: 2}, "1" * 24, [False] * 24):
            with self.subTest(series=series), self.assertRaises((ValueError, TypeError)):
                pykalos.tramo_seasonality(series)
        class OversizedSeries:
            def __len__(self):
                return 2**31

            def __iter__(self):
                raise AssertionError("range must be checked before copying")

        with self.assertRaisesRegex(ValueError, "index range"):
            pykalos.tramo_seasonality(OversizedSeries())
        values = [float(i) for i in range(24)]
        for kwargs in ({"frequency": 4}, {"frequency": 12.0}, {"precision": 0},
                       {"log_preference": math.inf}, {"detect_seasonality": "False"},
                       {"precision": True}, {"robust": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, TypeError)):
                options = dict(log_preference=0., precision=1e-5)
                options.update(kwargs)
                pykalos.tramo_transform_decision(values, **options)
        original = list(values)
        first = pykalos.tramo_seasonality(iter(values))
        self.assertEqual(values, original)
        first["differenced"][0] = 99.
        self.assertNotEqual(pykalos.tramo_seasonality(values)["differenced"][0], 99.)
