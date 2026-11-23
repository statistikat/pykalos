"""Replay the pinned JVM WK and fitted TRAMO component corpora."""
import csv
from collections import defaultdict
from pathlib import Path
import struct
import unittest

import pykalos


EVIDENCE = Path(__file__).resolve().parents[1] / "vendor" / "kalos-evidence" / "native"
WK = EVIDENCE / "seats-wk-extraction"
BRIDGE = EVIDENCE / "tramo-seats-bridge"


def csv_records(name):
    with (WK / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def grouped_records(name):
    records = []
    for line in (BRIDGE / name).read_text().splitlines():
        tokens = line.split()
        if tokens[0] == "case":
            current = []
            records.append((tokens[1], current))
        current.append(tokens)
    return records


def from_hex(token):
    return struct.unpack(">d", bytes.fromhex(token))[0]


def bits(values):
    return struct.pack(f">{len(values)}d", *values)


def fitted_arguments(records):
    fields = {row[0]: row for row in records}
    domain, model, likelihood = fields["interpolated"], fields["model"], fields["likelihood"]
    year, month = map(int, domain[1:3])
    options = dict(series=[from_hex(v) for v in domain[4:]], start_year=year,
                   start_month=month, d=int(model[8]), bd=int(model[10]),
                   log=model[2] == "true", mean_correction=model[4] == "true",
                   effective=int(likelihood[4]), estimated=int(likelihood[6]),
                   ssq=from_hex(likelihood[2]), outliers=[])
    for key in ("phi", "bphi", "theta", "btheta"):
        options[key] = [from_hex(x.removesuffix("/Fixed")) for x in fields[key][2:]]
    for row in records:
        if row[0] == "variable" and row[1] in ("AO", "LS"):
            y, m, day = map(int, row[2].strip("()").split("-"))
            if day != 1:
                raise ValueError("expected the start of an observation month")
            options["outliers"].append(dict(type=row[1], position=12*(y-year)+m-month,
                                            coefficient=from_hex(row[-1])))
    return options


class SeatsOracle(unittest.TestCase):
    def test_wk(self):
        inputs, facts = defaultdict(list), defaultdict(list)
        for row in csv_records("inputs.csv"):
            inputs[row["id"]].append(row["line"])
        for row in csv_records("model-facts.csv"):
            facts[row["id"], row["key"]].append(row["value"])
        refusals = dict(x_quarterly="D11", x_var0="innovation variance 0",
                        x_kalman="KalmanSmoother", x_kalman_wn="KalmanSmoother")
        cases = csv_records("cases.csv")
        rows = points = 0
        for case in cases:
            cid = case["id"]
            with self.subTest(case=cid):
                def fields(key):
                    value, = (line[len(key)+1:] for line in inputs[cid] if line.startswith(key + " "))
                    return value.split()

                orders, flags, knobs = fields("req spec"), fields("req log"), fields("req knobs")
                year, month = map(int, case["start"].split())
                options = dict(series=list(map(float, fields("values"))), innovation_variance=float(flags[4]),
                               d=int(orders[1]), bd=int(orders[4]), log=flags[0] == "1",
                               mean_correction=flags[2] == "1", frequency=int(case["freq"]),
                               start_year=year, start_month=month, approximation=knobs[5].lower(),
                               forecast=int(knobs[6]), backcast=int(knobs[7]), bias=knobs[9].lower(),
                               method="burman" if knobs[8] == "Burman" else "kalman_smoother")
                options.update(zip(("xl", "epsphi", "rmod", "smod", "smod_pi"), map(float, knobs[:5])))
                for name in ("phi", "theta", "bphi", "btheta"):
                    options[name] = list(map(float, fields("req " + name)))
                if cid in refusals:
                    with self.assertRaisesRegex(ValueError, refusals[cid]):
                        pykalos.seats_extract_wk(**options)
                    continue
                result = pykalos.seats_extract_wk(**options)
                self.assertEqual([result["status"]], facts[cid, "status"])
                for phase, key in (("initial", "init"), ("final", "final")):
                    expected = facts[cid, key] if result["status"] == "ok" else []
                    self.assertEqual(len(result[phase]), len(expected))
                    for row, line in zip(result[phase], expected):
                        tokens = line.split()
                        self.assertEqual((row["component"], row["information"]), tuple(tokens[:2]))
                        self.assertEqual((row["start_year"], row["start_month"]),
                                         (int(tokens[5]), int(tokens[6])+1))
                        self.assertEqual(len(row["values"]), int(tokens[3]))
                        self.assertEqual(bits(row["values"]), bits(list(map(float, tokens[8:]))))
                        rows += 1
                        points += len(row["values"])
        self.assertEqual((len(cases), rows, points), (36, 1095, 58020))

    def test_fitted_tramo(self):
        fitted = dict(grouped_records("bridge.txt"))
        accepted = approximated = points = 0
        for cid, records in grouped_records("merge-x86_64.txt"):
            with self.subTest(case=cid):
                options = fitted_arguments(fitted[cid])
                header = records[0]
                options.update(backcast=int(header[4]), forecast=int(header[6]))
                approximated += header[10] == "true"
                result = pykalos.seats_from_tramo(**options)
                self.assertEqual(result["status"], "ok")
                for key, phase in (("wk", "final"), ("merged", "merged")):
                    rows = [row for row in records if row[0] == key]
                    points += check_hex_rows(self, result[phase], rows)
                accepted += 1
        self.assertEqual((accepted, approximated, points), (6, 2, 11343))

    def test_request_boundary(self):
        data = [1.] * 96
        for arguments in (dict(d=False), dict(d=1.0), dict(forecast=-(2**30)), dict(start_month=13),
                          dict(log="false"), dict(phi=[float("nan")]), dict(rmod=float("inf")),
                          dict(approximation="unknown")):
            with self.subTest(arguments=arguments), self.assertRaises((ValueError, TypeError)):
                pykalos.seats_extract_wk(data, 1, **arguments)
        with self.assertRaisesRegex(ValueError, "positive"):
            pykalos.seats_extract_wk([-1.]*96, 1, log=True)
        options = fitted_arguments(grouped_records("bridge.txt")[0][1])
        for changes, reason in ((dict(ssq=0), "likelihood"), (dict(effective=1), "likelihood"),
                                (dict(outliers=[dict(type="TC", position=0, coefficient=1.)]), "AO or LS"),
                                (dict(outliers=[dict(type="AO", position=-1, coefficient=1.)]), "position")):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, reason):
                pykalos.seats_from_tramo(**(options | changes))


def check_hex_rows(test, actual, records):
    test.assertEqual(len(actual), len(records))
    count = 0
    for row, tokens in zip(actual, records):
        test.assertEqual((row["component"], row["information"]), tuple(tokens[1:3]))
        test.assertEqual((row["start_year"], row["start_month"]), tuple(map(int, tokens[3:5])))
        test.assertEqual(len(row["values"]), int(tokens[5]))
        test.assertEqual(bits(row["values"]), bytes.fromhex("".join(tokens[6:])))
        count += len(row["values"])
    return count
