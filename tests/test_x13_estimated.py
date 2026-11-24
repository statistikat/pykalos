"""Stock X-13 templates replayed from complete dated observations."""
import unittest

import pykalos
from test_seats import EVIDENCE, bits, from_hex


def stock_cases(template):
    cases = {}
    for line in (EVIDENCE / "x13-estimated-templates" / "templates-x86_64.txt").read_text().splitlines():
        key, *fields = line.split()
        if key == "case":
            preset, cid = fields
            if preset == template:
                records = cases[cid] = {}
        elif preset == template:
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
                                 ("available", preset.upper(), records["selected"][0].lower(), "legacy"))
                self.assertEqual([fit["log"], fit["mean"]], [v == "true" for v in records["model"][:2]])
                self.assertEqual([fit[k] for k in ("p", "d", "q", "bp", "bd", "bq")], list(map(int, records["model"][2:])))
                self.assertEqual(bits([v for block in fit["coefficients"] for v in block]),
                                 bytes.fromhex("".join(records["arma"])))
                variables = fit["variables"]
                self.assertEqual(bits([v["coefficient"] for v in variables]), bytes.fromhex("".join(records["coefficients"])))
                if variables:
                    self.assertEqual(len(variables), 1)
                    self.assertEqual(variables[0]["name"], " ".join(records["variable"][:2]))
                    self.assertEqual((variables[0]["regeffect"], variables[0]["type"]), ("Irregular", 0))
                    self.assertEqual(variables[0]["position"], 48)
                selection = records["selected"]
                self.assertEqual(fit["selection"], dict(d7_henderson=int(selection[1]), final_henderson=int(selection[2]),
                                                       msr_filter=int(selection[3][3:])))
                self.assertEqual(fit["effective_observations"], int(records["likelihood"][0]))
                ll = from_hex(records["likelihood"][2])
                self.assertLessEqual(abs(fit["log_likelihood"] - ll), 1e-10 * max(1, abs(ll)))
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

    def test_stock_monthly_scope(self):
        capability = pykalos.capabilities()["estimated_x13"]
        self.assertEqual(capability["templates"], ("RSA0", "RSA1"))
        self.assertEqual((capability["frequency"], capability["forecast_months"]), (12, 12))
        base = dict(series=[1.] * 60, start_year=2000, start_month=1)
        for change in ({"template": "RSA2c"}, {"frequency": 4}, {"start_month": 13}, {"series": [float("nan")]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                pykalos.x13_estimated(**(base | change))
