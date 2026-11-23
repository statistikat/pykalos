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

    def test_request_boundary(self):
        data = [from_hex(x) for x in (EVIDENCE / "panel.txt").read_text().splitlines()[0].split()[2:]]
        spec = dict(start_year=1990, start_month=1, mean=True, significance=.01, precision=1e-3)
        for extra in (dict(frequency=4), dict(start_month=0), dict(start_year=False), dict(mean=1),
                      dict(significance=1.1), dict(precision=float("nan")), dict(precision=0),
                      dict(series=[1.]*22), dict(series=[complex(1, 0)]*90)):
            with self.subTest(extra=extra), self.assertRaises((TypeError, ValueError)):
                pykalos.tramo_calendar_f_test(**(dict(series=data) | spec | extra))
