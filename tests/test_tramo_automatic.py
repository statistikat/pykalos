"""Public TR1 preprocessing on complete dated observations."""
import unittest

import pykalos
from test_seats import bits, check_hex_rows, from_hex, grouped_records


def check_preprocessing(test, result, records):
    records_by_key = {row[0]: row for row in records}
    spec, params, lk, residual = (records_by_key[key] for key in ("model", "parameters", "likelihood", "residuals"))
    model, likelihood = result["model"], result["likelihood"]
    test.assertEqual((model["log"], model["mean_correction"]), (spec[2] == "true", spec[4] == "true"))
    test.assertEqual(model["orders"], dict(zip(("p", "d", "q", "bp", "bd", "bq"), map(int, spec[6:]))))
    parameters = [v for key in ("phi", "bphi", "theta", "btheta") for v in model[key]]
    test.assertEqual(bits(parameters), bytes.fromhex("".join(params[1:])))
    values = [likelihood[key] for key in ("log_likelihood", "transformation_adjustment", "adjusted_log_likelihood", "ssq")]
    test.assertEqual(bits(values), bytes.fromhex("".join(lk[1:5])))
    test.assertEqual((likelihood["effective"], likelihood["estimated"]), tuple(map(int, lk[5:])))
    tsres = result["residuals"]
    test.assertEqual((tsres["start_year"], tsres["start_month"], len(tsres["tsres"])), tuple(map(int, residual[1:4])))
    test.assertEqual(bits(tsres["tsres"]), bytes.fromhex("".join(residual[4:])))
    variables = [row for row in records if row[0] == "variable"]
    domain_year, domain_month = map(int, records_by_key["input"][1:3])
    test.assertEqual(len(result["variables"]), len(variables))
    for variable, row in zip(result["variables"], variables):
        test.assertEqual(variable["name"], " ".join(row[1:-1]))
        test.assertEqual(bits([variable["coefficient"]]), bytes.fromhex(row[-1]))
        if row[1] != "const":
            y, m, _ = map(int, row[2].strip("()").split("-"))
            test.assertEqual((variable["type"], variable["position"]), (row[1], 12*(y-domain_year)+m-domain_month))
    return len(tsres["tsres"])


class PublicTr1(unittest.TestCase):
    def test_captured_preprocessing(self):
        cases = grouped_records("rsa1-x86_64.txt")
        residuals = 0
        for cid, records in cases:
            with self.subTest(case=cid):
                domain = records[1]
                result = pykalos.estimate_tramo_tr1(list(map(from_hex, domain[4:])), start_year=int(domain[1]),
                                                    start_month=int(domain[2]))
                self.assertEqual(result["status"], "available")
                residuals += check_preprocessing(self, result, records)
        self.assertEqual((len(cases), residuals), (6, 570))

    def test_raw_rsa1_product(self):
        totals = [0, 0, 0]
        cases = grouped_records("rsa1-x86_64.txt")
        for cid, records in cases:
            with self.subTest(case=cid):
                domain = records[1]
                fit = pykalos.tramoseats_fit(list(map(from_hex, domain[4:])), template="RSA1",
                                            start_year=int(domain[1]), start_month=int(domain[2]))
                self.assertEqual((fit["status"], fit["preprocessing_status"], fit["template"]),
                                 ("ok", "available", "RSA1"))
                self.assertEqual(fit["mode"], "multiplicative" if fit["model"]["log"] else "additive")
                totals[0] += check_preprocessing(self, fit, records)
                product, = [r for r in records if r[0] == "product"]
                self.assertEqual(product[1:3], ["present", "changed"])
                self.assertEqual(fit["model_changed"], product[3] == "true")
                rows = [r for r in records if r[0] == "merged"]
                totals[1] += len(rows)
                totals[2] += check_hex_rows(self, fit["merged"], rows)
                for key, component in (("finalSA", "SeasonallyAdjusted"), ("finalTrend", "Trend"),
                                       ("finalSeasonal", "Seasonal"), ("finalIrregular", "Irregular")):
                    row, = [r for r in rows if r[1:3] == [component, "Value"]]
                    self.assertEqual(bits(fit[key]), bytes.fromhex("".join(row[6:])))
                self.assertEqual(fit["series_forecast_stdev_status"], "unavailable")
        self.assertEqual((len(cases), *totals), (6, 570, 60, 3960))
        capability = pykalos.capabilities()["tramo_seats_fit"]["by_template"]
        self.assertTrue(capability["RSA0"]["series_forecast_stdev"])
        self.assertFalse(capability["RSA1"]["series_forecast_stdev"])

    def test_rsa1_horizons(self):
        records = dict(grouped_records("rsa1-x86_64.txt"))["fit_noout"]
        _, year, month, n, *data = records[1]
        result = pykalos.tramoseats_fit(list(map(from_hex, data)), template="tr1", start_year=int(year),
                                      start_month=int(month), backcast=3, forecast=6)
        first = 12 * int(year) + int(month) - 1
        origin = {"Value": (first, int(n)), "Forecast": (first + int(n), 6), "Backcast": (first - 3, 3)}
        series = [row for row in result["merged"] if row["component"] == "Series"]
        self.assertEqual({row["information"] for row in series}, set(origin))
        for row in series:
            self.assertEqual((12*row["start_year"] + row["start_month"] - 1, len(row["values"])),
                             origin[row["information"]])
        self.assertEqual(result["template"], "RSA1")

    def test_refusals(self):
        spec = dict(series=[1.]*36, start_year=1990, start_month=1)
        for extra in (dict(series=[1.]*23), dict(series=[float("nan")]*36), dict(start_month=13),
                      dict(start_year=1.), dict(frequency=4)):
            with self.subTest(extra=extra), self.assertRaises((ValueError, TypeError)):
                pykalos.estimate_tramo_tr1(**(spec | extra))
