"""JVM qualification of the four explicit fixed-order estimation policies."""
import csv
import os
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


def read_req(path):
    """Parse a pinned KALOSREQ record into estimate_sarima_fixed kwargs."""
    spec, columns, jacobian = {}, [], 0.0
    blocks = {name:dict(initial=[], fixed=[]) for name in BLOCKS}
    coefficients, fixed = [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0] == "KALOSREQ":
            continue
        key, values = fields[0], fields[1:]
        if key == "series":
            spec["series"] = list(map(float, values))
        elif key == "missing":
            spec["missing"] = [c == "1" for c in values[0]]
        elif key == "scalar":
            spec["period"], spec["d"], spec["seasonal_d"] = map(int, values[:3])
        elif key == "design_column":
            columns.append(list(map(float, values)))
        elif key == "design_coefficients":
            coefficients = list(map(float, values))
        elif key == "design_fixed":
            fixed = [c == "1" for c in values]
        elif key.startswith("block_") and key.endswith("_initial"):
            blocks[key[len("block_"):-len("_initial")]]["initial"] = list(map(float, values))
        elif key.startswith("block_") and key.endswith("_fixed"):
            blocks[key[len("block_"):-len("_fixed")]]["fixed"] = [c == "1" for c in values]
        elif key == "control":
            spec["control"] = dict(eps=float(values[0]), feps=float(values[1]),
                                   maximum_likelihood=values[2] == "1", unit_root_search=values[3] == "1",
                                   corrected_degrees_of_freedom=values[4] == "1", fast_derivatives=values[5] == "1",
                                   starting_point=values[6], solver=values[7])
        elif key == "optimizer":
            spec["optimizer"] = {pair.split("=")[0]: int(pair.split("=")[1]) for pair in values}
        elif key == "jacobian":
            jacobian = float(values[0])
    spec["design"] = dict(columns=columns, coefficients=coefficients, fixed=fixed)
    spec["blocks"] = blocks
    return spec, jacobian


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
        # The M10-D eligibility widening (upstream a1e62ec/7c3eefd) retires the
        # "fully free blocks" refusal: a partially fixed request now runs the
        # SAME pinned LM machine through the reduced free-coordinate seam
        # (detail::SsqFixedSeam). The fixed slot returns bit-exactly and the
        # landing agrees with the BFGS route at this test's existing budgets.
        widened = pykalos.estimate_sarima_fixed(**(spec | {"control": lm}))
        fit = pykalos.estimate_sarima_fixed(**spec)
        self.assertEqual((widened["status"], widened["converged"]), ("converged", True))
        self.assertEqual(widened["coefficients"]["ma"], [.25])
        self.assertLess(abs(widened["log_likelihood"] - fit["log_likelihood"]), 1e-9)
        self.assertLessEqual(widened["log_likelihood"], float(reference["loglik"]) + 5e-4)
        self.assertEqual(fit["coefficients"]["ma"], [.25])
        # The widened route's JVM-pinned destinations and eval counts replay
        # from the lm-fixed-block corpus (pinned inputs and jdplus 3.9.0 x13/
        # tramo captures transcribed into pins.txt from the qualification
        # report tmp_opencode/m9-perf/lmext section 4). Budgets are the
        # qualification budgets of pins.txt: adjustedll 2e-8*(1+|pin|),
        # coefficients 1e-4*(1+|pin|) on both JVM frontends, with the BFGS
        # route on the same request as the cross-route witness. The
        # eval-count fixture of record is live only single-threaded, exactly
        # as the upstream C++ gate (check_pinned_lm_corpus) pins it.
        folder = EVIDENCE / "lm-fixed-block"
        verify_sha256sums(folder)
        saved = {name: os.environ.pop(name, None) for name in
                 ("KALOS_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")}
        cases = 0
        try:
            for name in saved:
                os.environ[name] = "1"
            for record in (folder / "pins.txt").read_text().splitlines():
                if not record or record.startswith("#"):
                    continue
                fields = record.split()
                case, request_file = fields[0], fields[1]
                pins = [[float(v) for v in fields[5:8]], [float(v) for v in fields[8:11]]]
                evaluations, status = int(fields[11]), fields[12]
                replay, jacobian = read_req(folder / request_file)
                self.assertLess(abs(float(fields[2]) - jacobian), 1e-9, case)
                bfgs = pykalos.estimate_sarima_fixed(**replay)
                self.assertEqual(bfgs["status"], "converged", case)
                fit_lm = pykalos.estimate_sarima_fixed(**(replay | {
                    "control": replay["control"] | {"solver": "pinned_levenberg_marquardt"}}))
                self.assertEqual(fit_lm["status"], status, case)
                self.assertTrue(fit_lm["converged"], case)
                passes = fit_lm["passes"]
                self.assertEqual([p["stage"] for p in passes],
                                 ["estimate", "ur_regular", "ur_seasonal"], case)
                self.assertTrue(passes[0]["attempted"] and passes[0]["accepted"], case)
                self.assertTrue(passes[0]["optimizer_status"].startswith("converged"), case)
                self.assertEqual(passes[0]["evaluations"], evaluations, case)
                self.assertLess(passes[0]["evaluations"], bfgs["passes"][0]["evaluations"], case)
                for outcome in (bfgs, fit_lm):
                    adjusted = outcome["log_likelihood"] + jacobian
                    for pin in (float(fields[3]), float(fields[4])):
                        self.assertLess(abs(adjusted - pin), 2e-8 * (1 + abs(pin)), case)
                coefficients = [fit_lm["coefficients"][block][0]
                                for block in ("ar", "ma", "seasonal_ma")]
                for pin in pins:
                    for actual, target in zip(coefficients, pin):
                        self.assertLess(abs(actual - target), 1e-4 * (1 + abs(target)), case)
                self.assertEqual(coefficients[1], .2, case)
                cases += 1
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        self.assertEqual(cases, 4)
        for options in (dict(d=1.), dict(period=True), dict(optimizer={"typo":2}),
                        dict(control=spec["control"]|{"starting_point":"unknown"}),
                        dict(control=spec["control"]|{"maximum_likelihood":False}),
                        dict(design=dict(columns=[[2]],coefficients=[0],fixed=[False])),
                        dict(blocks={"ma":dict(initial=[.2],fixed=None)}),
                        dict(blocks={"seasonal_ar":dict(initial=[.3,.2],fixed=[False])})):
            with self.subTest(options=options), self.assertRaises((ValueError,TypeError)):
                pykalos.estimate_sarima_fixed(**(spec|options))
