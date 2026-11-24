"""Stock X-13 templates replayed from complete dated observations."""
import unittest

import pykalos
from test_seats import EVIDENCE, bits, from_hex


def stock_cases(template, filename="templates-x86_64.txt"):
    cases = {}
    for line in (EVIDENCE / "x13-estimated-templates" / filename).read_text().splitlines():
        key, *fields = line.split()
        if key == "case":
            preset, cid = fields
            if preset == template:
                records = cases[cid] = {}
        elif preset == template:
            if key == "variable":
                records.setdefault("variables", []).append(fields)
            else:
                records[key] = fields
    return cases


class StockX13(unittest.TestCase):
    def check_model_and_products(self, preset):
        cases = stock_cases(preset)
        self.assertEqual(set(cases), {"air", "ao", "seas"})
        rows = 0
        for cid, records in cases.items():
            with self.subTest(case=cid, template=preset):
                first, *values = (EVIDENCE / "x13-refusal-jvm-profiles" / (cid + ".csv")).read_text().splitlines()
                year, month = map(int, first.split(","))
                fit = pykalos.x13_estimated(list(map(float, values)), template=preset, start_year=year, start_month=month)
                self.assertEqual((fit["status"], fit["template"], fit["mode"], fit["sigma"]),
                                 ("available", "RSA2c" if preset == "rsa2c" else preset.upper(), records["selected"][0].lower(), "legacy"))
                self.assertEqual([fit["log"], fit["mean"]], [v == "true" for v in records["model"][:2]])
                self.assertEqual([fit[k] for k in ("p", "d", "q", "bp", "bd", "bq")], list(map(int, records["model"][2:])))
                self.assertEqual(bits([v for block in fit["coefficients"] for v in block]),
                                 bytes.fromhex("".join(records["arma"])))
                effects = records.get("variables", [])
                reference_coefs = list(map(from_hex, records["coefficients"]))
                calendar = {r[0]: coef for r, coef in zip(effects, reference_coefs, strict=True) if r[-1] == "CalendarEffect"}
                if preset == "rsa2c":
                    self.assertEqual(fit["calendar"], dict(working_days=cid == "air",
                                     easter_duration=1 if cid == "air" else 0, coefficients=calendar))
                outliers = [(r, coef) for r, coef in zip(effects, reference_coefs, strict=True) if r[-1] != "CalendarEffect"]
                for actual, (ref, coef) in zip(fit["variables"], outliers, strict=True):
                    self.assertEqual((actual["name"], actual["type"], actual["regeffect"], actual["coefficient"]),
                                     (" ".join(ref[:2]), 0, "Irregular", coef))
                    y, m, _ = map(int, ref[1].strip("()").split("-"))
                    self.assertEqual(actual["position"], 12 * (y - year) + m - month)
                selection = records["selected"]
                self.assertEqual(fit["selection"], dict(d7_henderson=int(selection[1]), final_henderson=int(selection[2]),
                                                       msr_filter=int(selection[3][3:])))
                self.assertEqual(fit["effective_observations"], int(records["likelihood"][0]))
                effective, estimated, ll, ssq = records["likelihood"]
                self.assertEqual(fit["likelihood"], dict(effective=int(effective), estimated=int(estimated),
                                                         log_likelihood=from_hex(ll), ssq=from_hex(ssq)))
                self.assertEqual(fit["log_likelihood"], from_hex(ll))
                ry, rm, rn, *residuals = records["residuals"]
                fitted = fit["residuals"]
                self.assertEqual((fitted["start_year"], fitted["start_month"], len(fitted["tsres"])),
                                 (int(ry), int(rm), int(rn)))
                self.assertEqual(bits(fitted["tsres"]), bytes.fromhex("".join(residuals)))
                self.assertEqual(fit["domain"], dict(start_year=year, start_month=month, length=len(values)))
                products = dict(fit["tables"], final_sa=fit["finalSA"], final_trend=fit["finalTrend"],
                                final_irregular=fit["finalIrregular"], y_f=fit["forecast"]["series"],
                                forecast_sa=fit["forecast"]["sa"], forecast_trend=fit["forecast"]["trend"])
                for name, measured in products.items():
                    y, m, n, *reference = records[name]
                    domain = fit["forecast_domain"] if name in ("y_f", "forecast_sa", "forecast_trend") else fit["domain"]
                    self.assertEqual((domain["start_year"], domain["start_month"], len(measured)), (int(y), int(m), int(n)))
                    if name in ("y_f", "forecast_sa", "forecast_trend"):
                        self.assertEqual(domain["length"], 12)
                    for value, expected in zip(measured, map(from_hex, reference), strict=True):
                        self.assertLessEqual(abs(value - expected), 1e-8 * max(1, abs(expected)), name)
                    rows += 1
        self.assertEqual(rows, 42)

    def test_public_rsa0_model_and_products(self):
        self.check_model_and_products("rsa0")

    def test_public_rsa1_model_and_products(self):
        self.check_model_and_products("rsa1")

    def test_public_rsa2c_model_and_products(self):
        self.check_model_and_products("rsa2c")

    def test_public_stock_residual_diagnostics_and_forecast_uncertainty(self):
        fields = forecasts = 0
        for preset in ("rsa0", "rsa1", "rsa2c"):
            for cid, records in stock_cases(preset, "diagnostics-x86_64.txt").items():
                first, *raw = (EVIDENCE / "x13-refusal-jvm-profiles" / (cid + ".csv")).read_text().splitlines()
                year, month = map(int, first.split(","))
                args = dict(template=preset, start_year=year, start_month=month)
                values = list(map(float, raw))
                for horizon in (1, 7, 12, 24):
                    with self.subTest(case=cid, template=preset, horizon=horizon):
                        options = {} if horizon == 12 else dict(forecast_error_months=horizon)
                        fit = pykalos.x13_estimated(values, **args, **options)
                        y, m, count, *expected = records["y_ef_" + str(horizon)]
                        self.assertEqual(fit["series_forecast_stdev_status"], "available")
                        self.assertEqual(fit["series_forecast_stdev_domain"],
                                         dict(start_year=int(y), start_month=int(m), length=int(count)))
                        self.assertEqual(fit["forecast_domain"]["length"], 12)
                        for value, ref in zip(fit["series_forecast_stdev"], map(from_hex, expected), strict=True):
                            self.assertLessEqual(abs(value - ref), 2e-8 * (1 + abs(ref)))
                            forecasts += 1
                        if horizon == 12:
                            residuals = fit["residuals"]
                            self.assertEqual(residuals["ser"], from_hex(records["residuals.ser"][0]))
                            for stat, df in (("lb", 22), ("doornikhansen", 2)):
                                ref = records["residuals." + stat]
                                self.assertEqual((residuals[stat]["value"], residuals[stat]["pvalue"],
                                                  residuals[stat]["df"]), (from_hex(ref[0]), from_hex(ref[1]), df))
                            self.assertEqual(residuals["lb"]["lags"], 24)
                            fields += 5
        self.assertEqual((fields, forecasts), (45, 396))
        empty = pykalos.x13_estimated(values, **args, forecast_error_months=0)
        self.assertEqual((empty["series_forecast_stdev_status"], empty["series_forecast_stdev"]),
                         ("no_requested_predictions", []))

    def test_stock_monthly_scope(self):
        capability = pykalos.capabilities()["estimated_x13"]
        self.assertEqual(capability["templates"], ("RSA0", "RSA1", "RSA2c"))
        self.assertEqual((capability["frequency"], capability["forecast_months"]), (12, 12))
        base = dict(series=[1.] * 60, start_year=2000, start_month=1)
        for change in ({"forecast_error_months": -1}, {"template": "RSA5c"}, {"frequency": 4}, {"start_month": 13}, {"series": [float("nan")]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                pykalos.x13_estimated(**(base | change))
