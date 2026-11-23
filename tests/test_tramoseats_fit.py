"""Replay original observations through the complete monthly RSA0 entry."""
import math
import unittest

import pykalos

from test_seats import bits, check_hex_rows, from_hex, grouped_records


class Rsa0Fit(unittest.TestCase):
    def test_raw_series_oracle(self):
        cases = grouped_records("rsa0-x86_64.txt")
        residuals = dict(grouped_records("rsa0-residuals-x86_64.txt"))
        points = rows = residual_points = 0
        for cid, records in cases:
            with self.subTest(case=cid):
                domain, expected_fit = records[1], records[2]
                data = [from_hex(token) for token in domain[4:]]
                result = pykalos.tramoseats_fit(data, start_year=int(domain[1]), start_month=int(domain[2]))
                self.assertEqual((result["status"], result["method"], result["template"], result["mode"]),
                                 ("ok", "tramoseats", "RSA0", "additive"))
                self.assertEqual(result["series"], data)
                _, tsres, ser = residuals[cid]
                self.assertEqual((tsres[0], ser[0]), ("residuals.tsres", "residuals.ser"))
                residual = result["residuals"]
                self.assertEqual((residual["start_year"], residual["start_month"]), tuple(map(int, tsres[1:3])))
                self.assertEqual(len(residual["tsres"]), int(tsres[3]))
                self.assertEqual(bits(residual["tsres"]), bytes.fromhex("".join(tsres[4:])))
                self.assertEqual(bits([residual["ser"]]), bytes.fromhex(ser[1]))
                residual_points += len(residual["tsres"])
                model, likelihood = result["model"], result["likelihood"]
                self.assertEqual(model["orders"], dict(p=0, d=1, q=1, bp=0, bd=1, bq=1))
                self.assertEqual((model["phi"], model["bphi"], model["log"], model["mean_correction"]),
                                 ([], [], False, True))
                values = [*model["theta"], *model["btheta"], model["mean_coefficient"],
                          likelihood["log_likelihood"], likelihood["ssq"]]
                self.assertEqual(bits(values), bytes.fromhex("".join(expected_fit[1:6])))
                self.assertEqual((likelihood["effective"], likelihood["estimated"]),
                                 tuple(map(int, expected_fit[6:8])))
                self.assertEqual(model["innovation_variance"],
                                 likelihood["ssq"] / (likelihood["effective"] - likelihood["estimated"]))
                oracle = [row for row in records if row[0] == "merged"]
                points += check_hex_rows(self, result["merged"], oracle)
                rows += len(oracle)
                names = dict(SeasonallyAdjusted="finalSA", Trend="finalTrend",
                             Irregular="finalIrregular", Seasonal="finalSeasonal")
                for row in oracle:
                    if row[2] == "Value" and row[1] in names:
                        self.assertEqual(bits(result[names[row[1]]]), bytes.fromhex("".join(row[6:])))
        self.assertEqual((len(cases), rows, points, residual_points), (6, 60, 3960, 570))

    def test_preprocessing_and_wk_forecast_uncertainty(self):
        forecasts = dict(grouped_records("rsa0-forecast-errors-x86_64.txt"))
        for cid, records in grouped_records("rsa0-x86_64.txt"):
            with self.subTest(case=cid):
                domain = records[1]
                fit = pykalos.tramoseats_fit([from_hex(token) for token in domain[4:]],
                                            start_year=int(domain[1]), start_month=int(domain[2]))
                _, public, wk = forecasts[cid]
                self.assertEqual(fit["series_forecast_stdev_status"], "available")
                self.assertEqual(public[0], "y_ef")
                self.assertEqual(wk[0], "wk_series_stdev_forecast")
                self.assertEqual(fit["series_forecast_domain"], dict(start_year=int(public[1]),
                                start_month=int(public[2]), length=int(public[3])))
                rows = [r for r in fit["final"] if (r["component"], r["information"]) == ("Series", "StdevForecast")]
                row, = rows
                for target in (public, wk):
                    self.assertEqual((row["start_year"], row["start_month"]), tuple(map(int, target[1:3])))
                    self.assertEqual(int(target[3]), 24)
                self.assertEqual(bits(row["values"]), bytes.fromhex("".join(wk[4:])))
                errors = fit["series_forecast_stdev"]
                self.assertEqual(len(errors), 24)
                for actual, reference in zip(errors, map(from_hex, public[4:])):
                    self.assertLessEqual(abs(actual-reference), 2e-8 * (1 + abs(reference)))

    def check_diagnostic(self, corpus, name, df):
        raw = dict(grouped_records("rsa0-x86_64.txt"))
        count = 0
        for cid, records in grouped_records(corpus):
            domain = raw[cid][1]
            values = list(map(from_hex, domain[4:]))
            for row in records[1:]:
                with self.subTest(case=cid, entry=row[:3]):
                    if row[0] == "short":
                        n, innovations = map(int, row[1:3])
                        reference = row[3:5]
                    else:
                        self.assertEqual(row[0], "residuals." + name)
                        n, innovations = len(values), len(values) - 13
                        reference = row[1:3]
                    result = pykalos.tramoseats_fit(values[:n], start_year=int(domain[1]),
                                                    start_month=int(domain[2]))
                    residual = result["residuals"]
                    self.assertEqual(len(residual["tsres"]), innovations)
                    test = residual[name]
                    self.assertEqual(test["df"], df)
                    if name == "lb":
                        self.assertEqual(test["lags"], 24)
                    for key, token in zip(("value", "pvalue"), reference):
                        if math.isnan(from_hex(token)):
                            self.assertTrue(math.isnan(test[key]))
                        else:
                            self.assertEqual(bits([test[key]]), bytes.fromhex(token))
                    count += 1
        self.assertEqual(count, 9)

    def test_residual_independence(self):
        self.check_diagnostic("rsa0-ljung-box-x86_64.txt", "lb", 22)
        self.assertTrue(pykalos.capabilities()["tramo_seats_fit"]["residual_ljung_box"])

    def test_residual_normality(self):
        self.check_diagnostic("rsa0-doornik-hansen-x86_64.txt", "doornikhansen", 2)
        self.assertTrue(pykalos.capabilities()["tramo_seats_fit"]["residual_doornik_hansen"])
        case = dict(grouped_records("rsa0-x86_64.txt"))["fit_tr0_air"][1]
        values = list(map(from_hex, case[4:24]))
        fit = pykalos.tramoseats_fit(values, start_year=int(case[1]), start_month=int(case[2]))
        self.assertEqual(len(fit["residuals"]["tsres"]), 7)
        self.assertIsNone(fit["residuals"]["doornikhansen"])

    def test_horizons_and_refusals(self):
        domain = grouped_records("rsa0-x86_64.txt")[0][1][1]
        data = [from_hex(token) for token in domain[4:]]
        fit = pykalos.tramoseats_fit(data, template="tr0", start_year=2010, start_month=3, forecast=6, backcast=3)
        spans = {r["information"]: (r["start_year"], r["start_month"], len(r["values"]))
                 for r in fit["merged"] if r["component"] == "Series"}
        self.assertEqual(len(fit["series_forecast_stdev"]), 6)
        self.assertEqual(spans, dict(Backcast=(2009, 12, 3), Value=(2010, 3, len(data)), Forecast=(2022, 3, 6)))
        no_forecast = pykalos.tramoseats_fit(data, forecast=0)
        self.assertEqual({r["information"] for r in no_forecast["merged"]}, {"Value"})
        self.assertEqual(no_forecast["series_forecast_stdev_status"], "no_requested_predictions")
        self.assertEqual(no_forecast["series_forecast_stdev"], [])
        for args, reason in ((dict(template="RSA1"), "RSA0"), (dict(frequency=4), "monthly"),
                             (dict(series=[1.]*12), "degrees of freedom"), (dict(series=[float("nan")]), "finite"),
                             (dict(forecast=1.), "integer"), (dict(backcast=-(2**30)), "range")):
            with self.subTest(args=args), self.assertRaisesRegex((ValueError, TypeError), reason):
                pykalos.tramoseats_fit(**(dict(series=data) | args))
        self.assertEqual(pykalos.capabilities()["tramo_seats_fit"]["templates"], ("RSA0",))
        self.assertFalse(pykalos.capabilities()["fit"])
