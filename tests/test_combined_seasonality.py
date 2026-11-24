"""Public combined SI diagnostics from the installed Python fit entry points."""
import unittest

import pykalos
from test_seats import EVIDENCE, from_hex, grouped_records
from test_x13_automatic import CORPUS, TYPE_NAMES


def panel(name):
    cases = []
    for line in (EVIDENCE / "combined-seasonality" / (name + "-x86_64.txt")).read_text().splitlines():
        tag, *values = line.split()
        if tag == "case":
            cid, source, mul = values
            facts = {}
            cases.append((cid, source, mul == "true", facts))
        else:
            facts[tag] = values
    return cases


class CombinedSi(unittest.TestCase):
    def check_diagnostic(self, result, ref):
        combined = result["diagnostics"]["combined_seasonality"]
        self.assertEqual(combined["summary"], ref["summary"][0])
        values = [combined[test][key] for test in ("stable", "moving", "kruskal_wallis")
                  for key in ("value", "pvalue")]
        for actual, expected in zip(values, map(from_hex, ref["statistics"]), strict=True):
            self.assertLessEqual(abs(actual - expected), 1e-12 * (1 + abs(expected)))

    def test_twenty_wk_products(self):
        inputs = dict(grouped_records("rsa3-x86_64.txt") + grouped_records("rsa3-ref-retry-x86_64.txt"))
        checked = 0
        for case, source, _, facts in panel("public"):
            if not source.startswith("wk_"):
                continue
            template, cid = case.split("_", 1)
            with self.subTest(case=case):
                _, y, m, _, *data = inputs[cid][1]
                fit = pykalos.tramoseats_fit(list(map(from_hex, data)), start_year=int(y), start_month=int(m), template=template)
                self.check_diagnostic(fit, facts)
                checked += 1
        self.assertEqual(checked, 20)

    def test_four_fixed_modes(self):
        _, _, _, _, *data = dict(grouped_records("rsa3-x86_64.txt"))["fit_tr0_air"][1]
        series = list(map(from_hex, data))
        modes = dict(Additive="additive", Multiplicative="multiplicative", LogAdditive="log_additive", PseudoAdditive="pseudo_additive")
        cases = panel("fixed-x13")
        self.assertEqual(len(cases), 4)
        for cid, _, log, facts in cases:
            mode = modes[cid.split("_")[1]]
            with self.subTest(mode=mode):
                fit = pykalos.x13_fit(series, seasonal=["s3x5"] * 12, trend_length=13, mode=mode, log=log)
                self.assertEqual(fit["mode_effective"], mode)
                self.check_diagnostic(fit, facts)
        unavailable = pykalos.x13_fit(series, seasonal=["s3x5"] * 12, trend_length=13, forecast=1)
        self.assertIsNone(unavailable["diagnostics"]["combined_seasonality"])

    def test_six_automatic_mode_and_domain_combinations(self):
        modes = {"Undefined": "additive", "LogAdditive": "log_additive", "PseudoAdditive": "pseudo_additive"}
        cases = panel("automatic-x13")
        self.assertEqual(len(cases), 6)
        for cid, _, _, facts in cases:
            base, mode, nb, nf = cid.rsplit("_", 3)
            c = CORPUS[base]
            with self.subTest(case=cid):
                fit = pykalos.x13_automatic(c["values"], start_year=c["first_year"], start_period=c["first_period"],
                    mode=modes[mode], backcast=int(nb), forecast=int(nf), sigma="accurate", lower_sigma=c["lower_sigma"],
                    upper_sigma=c["upper_sigma"], outliers=c["outliers"], outlier_types=[TYPE_NAMES[t] for t in c["otypes"]],
                    aicc_log_correction=c["aicc_log_correction"], ub1=c["ub1"], ub2=c["ub2"], cancel=c["cancel"],
                    tcrate=c["tcrate"], mixed=c["mixed"], balanced=c["balanced"], ljung_box_limit=c["ljung_box_limit"],
                    reduce_va=c["reduce_va"])
                self.check_diagnostic(fit, facts)

    def test_all_stock_calendar_and_estimated_products(self):
        inputs = dict(grouped_records("rsafull-x86_64.txt") + grouped_records("rsafull-late-calendar-x86_64.txt"))
        cases = panel("stock") + panel("stock-rsa2c")
        self.assertEqual(len(cases), 38)
        for case, _, _, facts in cases:
            with self.subTest(case=case):
                if case.startswith("rsafull_"):
                    _, cid = case.split("_", 1)
                    _, y, m, _, *data = inputs[cid][1]
                    result = pykalos.tramoseats_fit(list(map(from_hex, data)), template="RSAfull",
                                                    start_year=int(y), start_month=int(m))
                else:
                    _, preset, cid = case.split("_")
                    first, *data = (EVIDENCE / "x13-refusal-jvm-profiles" / (cid + ".csv")).read_text().splitlines()
                    y, m = map(int, first.split(","))
                    result = pykalos.x13_estimated(list(map(float, data)), template=preset, start_year=y, start_month=m)
                self.check_diagnostic(result, facts)
