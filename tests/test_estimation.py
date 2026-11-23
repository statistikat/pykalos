"""JVM qualification of the four explicit fixed-order estimation policies."""
import csv
from pathlib import Path
import unittest

import pykalos
from x13auto_corpus import verify_sha256sums


EVIDENCE = Path(__file__).resolve().parents[1] / "vendor/kalos-evidence/native"
BLOCKS = ("ar", "ma", "seasonal_ar", "seasonal_ma")


def numbers(text, convert=float):
    return list(map(convert, text.split(";"))) if text else []


def read(path):
    with path.open(newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def request(source, expected):
    data = numbers(source["y"])
    positions = numbers(source["missing"], int)
    columns = [numbers(text) for text in source["columns"].split("|")] if source["columns"] else []
    orders = [int(source[key]) for key in ("p_ar", "p_ma", "p_sar", "p_sma")]
    blocks = {name:dict(initial=[0.]*order, fixed=[False]*order) for name,order in zip(BLOCKS, orders)}
    control = dict(eps=float(expected.get("eps", 1e-7)), feps=float(expected.get("feps", 1e-4)),
                   maximum_likelihood=True, unit_root_search=False, corrected_degrees_of_freedom=True,
                   fast_derivatives=True, starting_point=source["start"].replace("HannanRissanen","hannan_rissanen").lower(),
                   solver="bfgs")
    return dict(series=data, missing=[i in positions for i in range(1,len(data)+1)],
                design=dict(columns=columns, coefficients=[0.]*len(columns), fixed=[False]*len(columns)),
                blocks=blocks, period=12, d=int(source["d"]), seasonal_d=int(source["D"]), control=control)


class EstimationControl(unittest.TestCase):
    def test_corpora(self):
        count = 0
        for name in ("estimation-control", "estimation-control-hr"):
            folder = EVIDENCE / name
            verify_sha256sums(folder)
            sources, expected = read(folder / "inputs.csv"), read(folder / "cases.csv")
            self.assertEqual(set(sources), set(expected))
            for cid, case in expected.items():
                with self.subTest(case=cid):
                    args = request(sources[cid], case)
                    result = pykalos.estimate_sarima_fixed(**args)
                    coeffs = result["coefficients"]
                    for block in BLOCKS:
                        self.assertEqual(len(coeffs[block]), len(args["blocks"][block]["initial"]))
                    ref = float(case["loglik"])
                    if cid.startswith("guard_"):
                        self.assertEqual((result["status"],result["converged"],result["passes"]),
                                         ("likelihood_only",False,[]))
                        self.assertLess(abs(result["log_likelihood"]-ref),1e-9)
                    else:
                        params = [v for key in ("ar","seasonal_ar","ma","seasonal_ma") for v in coeffs[key]]
                        wanted = numbers(case["params"])
                        self.assertEqual(len(params), len(wanted))
                        for actual, target in zip(params,wanted):
                            self.assertLess(abs(actual-target),2e-3)
                        self.assertLess(abs(result["log_likelihood"]-ref),5e-4)
                        passes = result["passes"]
                        chain = ["estimate","ur_regular","ur_seasonal"]
                        stages = []
                        if case["start"] in ("Multiple","HannanRissanen"):
                            stages.append("initialize")
                            self.assertEqual(passes[0]["detail"], "fitted,stabilized" if cid=="hrs_near_unit" else "fitted")
                        if case["start"] == "Multiple":
                            for prefix in ("multiple_first.","multiple_second."):
                                stages.extend(prefix + item for item in chain)
                        stages.extend(chain)
                        self.assertEqual([p["stage"] for p in passes], stages)
                        for pos,p in enumerate(passes):
                            if p["stage"].endswith("ur_regular") or p["stage"].endswith("ur_seasonal"):
                                self.assertFalse(p["accepted"] and not p["attempted"])
                                if p["attempted"]:
                                    base = pos - (1 if p["stage"].endswith("regular") else 2)
                                    self.assertEqual(p["accepted"], p["log_likelihood"]>passes[base]["log_likelihood"])
                    count += 1
        self.assertEqual(count, 27)

    def test_fixed_coordinate_and_refusals(self):
        folder = EVIDENCE / "estimation-control"
        spec = request(read(folder / "inputs.csv")["zero_r11"],read(folder / "cases.csv")["zero_r11"])
        lm = spec["control"] | {"solver": "pinned_levenberg_marquardt"}
        reference = read(folder / "cases.csv")["zero_r11"]
        pinned = pykalos.estimate_sarima_fixed(**(spec | {"control": lm}))
        self.assertLess(abs(pinned["log_likelihood"] - float(reference["loglik"])), 1e-9)
        model = pinned["coefficients"]
        for fitted, expected in zip(model["ar"] + model["ma"], numbers(reference["params"])):
            self.assertLess(abs(fitted - expected), 1e-8)
        spec["blocks"]["ma"] = dict(initial=[.25], fixed=[True])
        with self.assertRaisesRegex(ValueError, "fully free blocks"):
            pykalos.estimate_sarima_fixed(**(spec | {"control": lm}))
        fit = pykalos.estimate_sarima_fixed(**spec)
        self.assertEqual(fit["coefficients"]["ma"], [.25])
        for options in (dict(d=1.), dict(period=True), dict(optimizer={"typo":2}),
                        dict(control=spec["control"]|{"starting_point":"unknown"}),
                        dict(control=spec["control"]|{"maximum_likelihood":False}),
                        dict(design=dict(columns=[[2]],coefficients=[0],fixed=[False])),
                        dict(blocks={"ma":dict(initial=[.2],fixed=None)}),
                        dict(blocks={"seasonal_ar":dict(initial=[.3,.2],fixed=[False])})):
            with self.subTest(options=options), self.assertRaises((ValueError,TypeError)):
                pykalos.estimate_sarima_fixed(**(spec|options))
