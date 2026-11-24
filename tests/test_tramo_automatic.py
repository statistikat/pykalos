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


def rsa1_reference_inputs():
    corpora = {"": "rsa1", "level_": "rsa1-level-effects",
               "level_tc_": "rsa1-level-tc", "log_tc_": "rsa1-log-tc"}
    return {prefix + cid: rows for prefix, corpus in corpora.items()
            for cid, rows in grouped_records(corpus + "-x86_64.txt")}


def check_public_diagnostics(test, actual, records):
    facts = {row[0]: row[1:] for row in records}
    test.assertEqual(bits([actual["ser"]]), bytes.fromhex(facts["residuals.ser"][0]))
    test.assertEqual(actual["lb"]["lags"], 24)
    for key in ("lb", "doornikhansen"):
        fact = facts["residuals." + key]
        test.assertEqual(actual[key]["df"], float(fact[4]))
        test.assertEqual(bits([actual[key]["value"], actual[key]["pvalue"]]), bytes.fromhex("".join(fact[:2])))


def rsa3_reference_inputs():
    return dict(case for corpus in ("rsa3", "rsa3-additional", "rsa3-mean-retry")
                for case in grouped_records(corpus + "-x86_64.txt"))


def check_forecast_errors(test, template, inputs, forecasts):
    test.assertEqual(set(inputs), set(forecasts))
    for cid, records in inputs.items():
        _, year, month, _, *data = records[1]
        series = list(map(from_hex, data))
        facts = {r[0]: r for r in forecasts[cid]}
        public = facts["y_ef"]
        wk = facts["wk_series_stdev_forecast"]
        for count in (0, 7, -2):
            with test.subTest(case=cid, forecast=count):
                fit = pykalos.tramoseats_fit(series, template=template, start_year=int(year),
                                            start_month=int(month), forecast=count)
                length = 24 if count == -2 else count
                test.assertEqual(fit["series_forecast_domain"],
                                 dict(start_year=int(public[1]), start_month=int(public[2]), length=length))
                test.assertEqual(fit["series_forecast_stdev_status"], "available" if count else "no_requested_predictions")
                errors = fit["series_forecast_stdev"]
                test.assertEqual(len(errors), length)
                for actual, expected in zip(errors, map(from_hex, public[4:])):
                    test.assertLessEqual(abs(actual - expected), 2e-8 * (1 + abs(expected)))
                if count == -2:
                    row, = [r for r in fit["final"] if (r["component"], r["information"]) == ("Series", "StdevForecast")]
                    test.assertEqual(bits(row["values"]), bytes.fromhex("".join(wk[4:])))


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
                self.assertEqual(fit["series_forecast_stdev_status"], "available")
        self.assertEqual((len(cases), *totals), (6, 570, 60, 3960))
        capability = pykalos.capabilities()["tramo_seats_fit"]["by_template"]
        self.assertTrue(capability["RSA0"]["series_forecast_stdev"])
        self.assertTrue(capability["RSA1"]["series_forecast_stdev"])

    def test_rsa1_outlier_restoration(self):
        scope = pykalos.capabilities()["tramo_seats_fit"]["by_template"]["RSA1"]["restored_outliers_by_mode"]
        self.assertEqual(scope, {mode: ("AO", "LS", "TC") for mode in ("additive", "multiplicative")})
        cases = residuals = values = 0
        for corpus in ("rsa1-level-effects", "rsa1-level-tc", "rsa1-log-tc"):
            for cid, records in grouped_records(corpus + "-x86_64.txt"):
                with self.subTest(corpus=corpus, case=cid):
                    _, year, month, _, *data = records[1]
                    series = list(map(from_hex, data))
                    domain = dict(start_year=int(year), start_month=int(month))
                    raw = pykalos.tramoseats_fit(series, template="RSA1", **domain)
                    residuals += check_preprocessing(self, raw, records)
                    model = raw["model"]
                    likelihood = raw["likelihood"]
                    spec = {k: model[k] for k in ("phi", "theta", "bphi", "btheta", "log", "mean_correction")}
                    spec.update({k: model["orders"][k] for k in ("d", "bd")})
                    spec.update({k: likelihood[k] for k in ("ssq", "effective", "estimated")})
                    effects = [{k: v[k] for k in ("type", "position", "coefficient")}
                               for v in raw["variables"] if "type" in v]
                    fitted = pykalos.seats_from_tramo(series, outliers=effects, **domain, **spec)
                    expected = [r for r in records if r[0] == "merged"]
                    self.assertEqual((raw["status"], fitted["status"]), ("ok", "ok"))
                    product, = (r for r in records if r[0] == "product")
                    self.assertEqual(raw["model_changed"], product[3] == "true")
                    values += check_hex_rows(self, raw["merged"], expected)
                    check_hex_rows(self, fitted["merged"], expected)
                    cases += 1
        self.assertEqual((cases, residuals, values), (6, 498, 3600))

    def test_public_rsa1_residual_diagnostics(self):
        inputs = rsa1_reference_inputs()
        diagnostics = dict(grouped_records("rsa1-residual-diagnostics-x86_64.txt"))
        self.assertEqual(set(diagnostics), set(inputs))
        self.assertEqual(len(inputs), 12)
        for cid, records in inputs.items():
            _, year, month, _, *data = records[1]
            series = list(map(from_hex, data))
            domain = dict(start_year=int(year), start_month=int(month))
            facts = {r[0]: r[1:] for r in diagnostics[cid]}
            for fn, options in ((pykalos.estimate_tramo_tr1, domain),
                                (pykalos.tramoseats_fit, domain | {"template": "RSA1"})):
                with self.subTest(case=cid, route=fn.__name__):
                    residual = fn(series, **options)["residuals"]
                    self.assertEqual(bits([residual["ser"]]), bytes.fromhex(facts["residuals.ser"][0]))
                    self.assertEqual(residual["lb"]["lags"], 24)
                    for key, df in (("lb", 22), ("doornikhansen", 2)):
                        test = residual[key]
                        self.assertEqual(test["df"], df)
                        self.assertEqual(bits([test["value"], test["pvalue"]]),
                                         bytes.fromhex("".join(facts["residuals." + key][:2])))
        templates = pykalos.capabilities()["tramo_seats_fit"]["by_template"]
        self.assertEqual(templates["RSA1"]["residuals"], ("tsres", "ser", "lb", "doornikhansen"))

    def test_raw_rsa1_public_forecast_errors(self):
        check_forecast_errors(self, "RSA1", rsa1_reference_inputs(),
                              dict(grouped_records("rsa1-forecast-errors-x86_64.txt")))

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


class PublicTr3(unittest.TestCase):
    def test_raw_rsa3_product(self):
        cases = rsa3_reference_inputs().items()
        residuals = rows = values = 0
        for cid, records in cases:
            with self.subTest(case=cid):
                _, year, month, _, *data = records[1]
                series = list(map(from_hex, data))
                domain = dict(start_year=int(year), start_month=int(month))
                raw = pykalos.tramoseats_fit(series, template="tr3", **domain)
                self.assertEqual((raw["status"], raw["preprocessing_status"], raw["template"]),
                                 ("ok", "available", "RSA3"))
                self.assertEqual(raw["mode"], "multiplicative" if raw["model"]["log"] else "additive")
                residuals += check_preprocessing(self, raw, records)
                self.assertEqual(set(raw["residuals"]), {"tsres", "start_year", "start_month", "ser", "lb", "doornikhansen"})
                fitted = pykalos.estimate_tramo_tr3(series, **domain)
                self.assertEqual(fitted["status"], "available")
                check_preprocessing(self, fitted, records)
                product, = (row for row in records if row[0] == "product")
                self.assertEqual(raw["model_changed"], product[3] == "true")
                expected = [row for row in records if row[0] == "merged"]
                rows += len(expected)
                values += check_hex_rows(self, raw["merged"], expected)
                for key, component in (("finalSA", "SeasonallyAdjusted"), ("finalTrend", "Trend"),
                                       ("finalSeasonal", "Seasonal"), ("finalIrregular", "Irregular")):
                    row, = (r for r in expected if r[1:3] == [component, "Value"])
                    self.assertEqual(bits(raw[key]), bytes.fromhex("".join(row[6:])))
                self.assertEqual(raw["series_forecast_stdev_status"], "available")
        self.assertEqual((len(cases), residuals, rows, values), (13, 1196, 130, 8340))

    def test_horizons_and_capabilities(self):
        _, year, month, n, *data = grouped_records("rsa3-x86_64.txt")[0][1][1]
        domain = dict(start_year=int(year), start_month=int(month))
        start = 12 * int(year) + int(month) - 1
        for horizon in (0, 7):
            with self.subTest(horizon=horizon):
                fit = pykalos.tramoseats_fit(list(map(from_hex, data)), template="RSA3", forecast=horizon, **domain)
                rows = {row["information"]: row for row in fit["merged"] if row["component"] == "Series"}
                self.assertEqual(set(rows), {"Value", "Forecast"} if horizon else {"Value"})
                if horizon:
                    forecast = rows["Forecast"]
                    self.assertEqual((12*forecast["start_year"] + forecast["start_month"]-1, len(forecast["values"])),
                                     (start + int(n), horizon))
                self.assertEqual(fit["series_forecast_stdev_status"], "available" if horizon else "no_requested_predictions")
        cap = pykalos.capabilities()["tramo_seats_fit"]["by_template"]["RSA3"]
        self.assertEqual(cap["residuals"], ("tsres", "ser", "lb", "doornikhansen"))
        self.assertTrue(cap["automatic_identification"])
        self.assertTrue(cap["series_forecast_stdev"])
        for extra in (dict(series=[1.]*23), dict(series=[float("nan")]*36), dict(start_month=13), dict(frequency=4)):
            with self.subTest(extra=extra), self.assertRaises((ValueError, TypeError)):
                pykalos.estimate_tramo_tr3(**(dict(series=[1.]*48) | domain | extra))

    def test_public_residual_diagnostics(self):
        inputs = rsa3_reference_inputs()
        tests = dict(case for corpus in ("rsa3-residual-diagnostics", "rsa3-mean-retry-diagnostics")
                     for case in grouped_records(corpus + "-x86_64.txt"))
        self.assertEqual(set(tests), set(inputs))
        self.assertEqual(len(inputs), 13)
        for cid, records in inputs.items():
            _, year, month, _, *data = records[1]
            domain = dict(start_year=int(year), start_month=int(month))
            series = list(map(from_hex, data))
            for route, options in ((pykalos.estimate_tramo_tr3, domain),
                                   (pykalos.tramoseats_fit, domain | {"template": "RSA3"})):
                with self.subTest(case=cid, route=route.__name__):
                    check_public_diagnostics(self, route(series, **options)["residuals"], tests[cid])

    def test_raw_rsa3_public_forecast_errors(self):
        check_forecast_errors(self, "RSA3", rsa3_reference_inputs(),
                              dict(grouped_records("rsa3-forecast-errors-x86_64.txt")))

    def test_standalone_reference_retries(self):
        cases = dict(grouped_records("rsa3-ref-retry-x86_64.txt"))
        diagnostics = dict(grouped_records("rsa3-ref-retry-diagnostics-x86_64.txt"))
        self.assertEqual(set(cases), set(diagnostics))
        residuals = 0
        for cid, records in cases.items():
            with self.subTest(case=cid):
                _, year, month, _, *data = records[1]
                fit = pykalos.estimate_tramo_tr3(list(map(from_hex, data)), start_year=int(year), start_month=int(month))
                residuals += check_preprocessing(self, fit, records)
                check_public_diagnostics(self, fit["residuals"], diagnostics[cid])
        self.assertEqual((len(cases), residuals), (7, 909))

    def test_reference_retry_products(self):
        inputs = dict(grouped_records("rsa3-ref-retry-x86_64.txt"))
        # The seasonal-only AR model still needs its WK extraction qualification.
        del inputs["fit_ref_retry_18_2"]
        forecasts = dict(grouped_records("rsa3-ref-retry-forecast-errors-x86_64.txt"))
        diagnostics = dict(grouped_records("rsa3-ref-retry-diagnostics-x86_64.txt"))
        values = rows = 0
        for cid, records in inputs.items():
            with self.subTest(case=cid):
                _, year, month, _, *data = records[1]
                raw = pykalos.tramoseats_fit(list(map(from_hex, data)), template="RSA3",
                                            start_year=int(year), start_month=int(month))
                self.assertEqual(raw["status"], "ok")
                check_preprocessing(self, raw, records)
                check_public_diagnostics(self, raw["residuals"], diagnostics[cid])
                expected = [r for r in records if r[0] == "merged"]
                rows += len(expected)
                values += check_hex_rows(self, raw["merged"], expected)
        self.assertEqual((len(inputs), rows, values), (6, 60, 4560))
        check_forecast_errors(self, "RSA3", inputs, {cid: forecasts[cid] for cid in inputs})
