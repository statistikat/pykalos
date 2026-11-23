"""Replay original observations through the complete monthly RSA0 entry."""
import unittest

import pykalos

from test_seats import bits, check_hex_rows, from_hex, grouped_records


class Rsa0Fit(unittest.TestCase):
    def test_raw_series_oracle(self):
        cases = grouped_records("rsa0-x86_64.txt")
        points = rows = 0
        for cid, records in cases:
            with self.subTest(case=cid):
                domain, expected_fit = records[1], records[2]
                data = [from_hex(token) for token in domain[4:]]
                result = pykalos.tramoseats_fit(data, start_year=int(domain[1]), start_month=int(domain[2]))
                self.assertEqual((result["status"], result["method"], result["template"], result["mode"]),
                                 ("ok", "tramoseats", "RSA0", "additive"))
                self.assertEqual(result["series"], data)
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
        self.assertEqual((len(cases), rows, points), (6, 60, 3960))

    def test_horizons_and_refusals(self):
        domain = grouped_records("rsa0-x86_64.txt")[0][1][1]
        data = [from_hex(token) for token in domain[4:]]
        fit = pykalos.tramoseats_fit(data, template="tr0", start_year=2010, start_month=3, forecast=6, backcast=3)
        spans = {r["information"]: (r["start_year"], r["start_month"], len(r["values"]))
                 for r in fit["merged"] if r["component"] == "Series"}
        self.assertEqual(spans, dict(Backcast=(2009, 12, 3), Value=(2010, 3, len(data)), Forecast=(2022, 3, 6)))
        no_forecast = pykalos.tramoseats_fit(data, forecast=0)
        self.assertEqual({r["information"] for r in no_forecast["merged"]}, {"Value"})
        for args, reason in ((dict(template="RSA1"), "RSA0"), (dict(frequency=4), "monthly"),
                             (dict(series=[1.]*12), "degrees of freedom"), (dict(series=[float("nan")]), "finite"),
                             (dict(forecast=1.), "integer"), (dict(backcast=-(2**30)), "range")):
            with self.subTest(args=args), self.assertRaisesRegex((ValueError, TypeError), reason):
                pykalos.tramoseats_fit(**(dict(series=data) | args))
        self.assertEqual(pykalos.capabilities()["tramo_seats_fit"]["templates"], ("RSA0",))
        self.assertFalse(pykalos.capabilities()["fit"])
