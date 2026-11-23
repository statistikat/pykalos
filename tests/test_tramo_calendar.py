"""Replay the direct monthly calendar candidate fits and threshold equalities."""
from pathlib import Path
import unittest

import pykalos
from test_seats import bits, from_hex
from x13auto_corpus import verify_sha256sums


EVIDENCE = Path(__file__).resolve().parents[1] / "vendor/kalos-evidence/native/tramo-calendar-ftest"


class CalendarFTest(unittest.TestCase):
    def test_pinned_panel(self):
        verify_sha256sums(EVIDENCE)
        inputs, selections = {}, []
        for line in (EVIDENCE / "panel.txt").read_text().splitlines():
            fields = line.split()
            if fields[0] == "input":
                inputs[fields[1]] = list(map(from_hex, fields[2:]))
                continue
            kind, label, cid, mean, alpha, ss0, nhp, df1, ss1, df6, ss6, selected, ms1, ms6, p1, p6 = fields
            with self.subTest(case=cid, threshold=label):
                self.assertEqual((kind, nhp), ("fit", "2"))
                result = pykalos.tramo_calendar_f_test(inputs[cid], start_year=1990, start_month=1,
                    mean=bool(int(mean)), significance=from_hex(alpha), precision=1e-3)
                self.assertEqual(bits([result["base_ssq"]]), bytes.fromhex(ss0))
                for name, df, ssq, ms, prob in (("working_days", df1, ss1, ms1, p1),
                                                ("trading_days", df6, ss6, ms6, p6)):
                    candidate = result[name]
                    self.assertEqual(candidate["degrees_of_freedom"], int(df))
                    self.assertEqual(bits([candidate["residual_ssq"], candidate["mean_square"],
                                           candidate["lower_probability"]]), bytes.fromhex(ssq + ms + prob))
                self.assertEqual(result["selected"], {"0":"none", "1":"working_days", "6":"trading_days"}[selected])
                selections.append(result["selected"])
        self.assertEqual((len(inputs), len(selections), len(set(selections))), (4, 14, 3))

    def test_stock_initial_calendar(self):
        count = 0
        for line in (EVIDENCE / "full.txt").read_text().splitlines():
            fields = line.split()
            if fields[0] == "input":
                _, cid, log, *data = fields
                fit = pykalos.tramo_full_initial_calendar(list(map(from_hex, data)), start_year=1990,
                                                         start_month=1, log=bool(int(log)))
                continue
            with self.subTest(case=cid, log=log):
                kind, status, columns, mean, lp, easter, base, one, six, p1, p6, mt, lt, et = fields
                self.assertEqual(kind, "result")
                report = fit["comparison"]
                self.assertEqual(report["selected"], {"0":"none", "1":"working_days", "6":"trading_days"}[columns])
                wd, td = report["working_days"], report["trading_days"]
                self.assertEqual(bits([report["base_ssq"], wd["residual_ssq"], td["residual_ssq"],
                                       wd["lower_probability"], td["lower_probability"]]),
                                 bytes.fromhex(base + one + six + p1 + p6))
                self.assertEqual(bits([fit["mean_t"], fit["easter_t"]]), bytes.fromhex(mt + et))
                if lt == "-":
                    self.assertIsNone(fit["leap_year_t"])
                else:
                    self.assertEqual(bits([fit["leap_year_t"]]), bytes.fromhex(lt))
                self.assertEqual((fit["keep_mean"], fit["keep_leap_year"], fit["keep_easter"]),
                                 tuple(v == "true" for v in (mean, lp, easter)))
                self.assertEqual(fit["module_changed"], status == "Changed")
                count += 1
        self.assertEqual(count, 20)
        for options in (dict(log=1), dict(log=True, series=[-1.]*180), dict(log=False, frequency=4)):
            with self.assertRaises((ValueError, TypeError)):
                pykalos.tramo_full_initial_calendar(**(dict(series=[1.]*180, start_year=1990, start_month=1) | options))

    def test_residual_trading_day_decisions(self):
        count = 0
        for line in (EVIDENCE / "residual-td.txt").read_text().splitlines():
            fields = line.split()
            if fields[0] == "residuals":
                year, month, n = map(int, fields[1:4])
                request = dict(residuals=list(map(from_hex, fields[4:])), estimation_start_year=year,
                               estimation_start_month=month, estimation_length=n)
                continue
            key, alpha, statistic, probability, selected = fields
            with self.subTest(year=year, month=month, threshold=alpha):
                self.assertEqual(key, "gate")
                result = pykalos.tramo_residual_trading_days(**request, significance=from_hex(alpha))
                self.assertEqual(bits([result["statistic"], result["upper_probability"]]),
                                 bytes.fromhex(statistic + probability))
                self.assertEqual(result["needs_processing"], selected == "true")
                count += 1
        self.assertEqual(count, 32)
        request = dict(estimation_start_year=1990, estimation_start_month=1, estimation_length=48, significance=.01)
        for data in ([], [1.], [0.]*36):
            self.assertIsNone(pykalos.tramo_residual_trading_days(data, **request))
        for options in (dict(estimation_start_month=13), dict(estimation_length=9), dict(significance=2.),
                        dict(frequency=4)):
            with self.subTest(options=options), self.assertRaises(ValueError):
                pykalos.tramo_residual_trading_days([1.]*36, **(request | options))

    def test_request_boundary(self):
        data = [from_hex(x) for x in (EVIDENCE / "panel.txt").read_text().splitlines()[0].split()[2:]]
        spec = dict(start_year=1990, start_month=1, mean=True, significance=.01, precision=1e-3)
        for extra in (dict(frequency=4), dict(start_month=0), dict(start_year=False), dict(mean=1),
                      dict(significance=1.1), dict(precision=float("nan")), dict(precision=0),
                      dict(series=[1.]*22), dict(series=[complex(1, 0)]*90)):
            with self.subTest(extra=extra), self.assertRaises((TypeError, ValueError)):
                pykalos.tramo_calendar_f_test(**(dict(series=data) | spec | extra))
