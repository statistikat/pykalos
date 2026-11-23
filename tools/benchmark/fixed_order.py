"""Replay the historical monthly fixed-order airline and mixed-factor matrix.

Requires an installed pykalos wheel and the original core validation checkout.
R/JVM versions, packages and JAR hashes are verified against its oracle manifest.
Set KALOS_NUM_THREADS, OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and
VECLIB_MAXIMUM_THREADS to 1. From the wheel's Python environment run
tools/benchmark/fixed_order.py --core ../kalos --cpu "<host CPU>"
--compiler "<wheel compiler>" --output timings.json.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

import pykalos
from pykalos import _kalos


def prepare(case):
    blocks = {k: dict(initial=list(map(float, b["initial"])), fixed=b["fixed"])
              for k, b in case["blocks"].items()}
    regressors = [dict(name=k, start=case["start"], values=list(map(float, values)))
                  for k, values in case["regressors"].items()]
    offset, end = case["rows"]
    offset -= 1
    data = list(map(float, case["values"]))
    design = pykalos.prepare_regression(
        len(data), start=case["start"], frequency=12, regressors=regressors,
        coefficients=[dict(name="fixed", value=.2, fixed=True)], estimation_start=case["from"],
        estimation_end=case["to"], d=case["d"], seasonal_d=case["D"], include_drift=True, forecast=12)
    transformed = pykalos.prepare_series(
        data[offset:end], transformation=case["transformation"], degree=case["d"] + 12 * case["D"],
        missing=case["missing"][offset:end], source_offset=offset)
    control = dict(eps=1e-12, feps=1e-4, maximum_likelihood=True, unit_root_search=False,
                   corrected_degrees_of_freedom=True, fast_derivatives=True, starting_point="zero", solver="bfgs")
    return dict(series=transformed["values"], missing=transformed["missing"], period=12,
                d=case["d"], seasonal_d=case["D"], blocks=blocks, design=design["design"],
                control=control, optimizer=dict(max_iterations=200, max_evaluations=4000)), transformed["log_jacobian"]


def verify(fit, jacobian, model, reference):
    if not fit["converged"]:
        raise ValueError(f"fixed-order estimation failed: {fit['status']}")

    def difference(actual, expected, tolerance):
        expected = float(expected)
        if not math.isfinite(actual) or abs(actual - expected) > tolerance * (1 + abs(expected)):
            raise ValueError(f"{actual} differs from {expected}, relative budget {tolerance}")
        return abs(actual - expected)

    worst = 0.
    for name, block in model.items():
        for actual, expected, initial, fixed in zip(fit["coefficients"][name], reference["coefficients"][name],
                                                   block["initial"], block["fixed"], strict=True):
            if fixed and (actual != initial or float(expected) != initial):
                raise ValueError("fixed coefficient changed")
            worst = max(worst, difference(actual, expected, 1e-4))
    return dict(coefficient_max_abs=worst, jacobian_abs=difference(jacobian, reference["jacobian"], 1e-10),
                adjustedll_abs=difference(fit["log_likelihood"] + jacobian, reference["adjustedll"], 2e-8))


def run(args):
    required = ("KALOS_NUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
    threads = {k: os.environ.get(k) for k in required}
    if set(threads.values()) != {"1"}:
        raise ValueError(f"set {', '.join(required)} to 1")
    if min(args.warmup, args.samples, args.batch) < 1:
        raise ValueError("warmup, samples and batch must be positive")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "reference.json"
        script = Path(__file__).with_name("fixed_order_reference.R")
        subprocess.run(["Rscript", "--vanilla", script, args.core, output, str(args.warmup),
                        str(args.samples), str(args.batch)], check=True)
        captured = json.loads(output.read_text())
    cases = {k: prepare(v) for k, v in captured["inputs"].items()}
    evidence = {}
    for cid, (spec, jacobian) in cases.items():
        fit = pykalos.estimate_sarima_fixed(**spec)
        try:
            evidence[cid] = {method: verify(fit, jacobian, spec["blocks"], captured[method]["expected"][cid])
                             for method in ("x13", "tramo")}
        except ValueError as err:
            raise ValueError(f"{cid}: {err}") from err
    for _ in range(args.warmup):
        for spec, _ in cases.values():
            pykalos.estimate_sarima_fixed(**spec)
    timings = {cid: [] for cid in cases}
    for _ in range(args.samples):
        for cid, (spec, jacobian) in cases.items():
            start = time.perf_counter_ns()
            for _ in range(args.batch):
                fit = pykalos.estimate_sarima_fixed(**spec)
            timings[cid].append((time.perf_counter_ns() - start) / (1e6 * args.batch))
            for method in ("x13", "tramo"):
                verify(fit, jacobian, spec["blocks"], captured[method]["expected"][cid])
    raw = dict(python=timings, x13=captured["x13"]["ms"], tramo=captured["tramo"]["ms"])
    summary = {name: {kind: statistics.mean(statistics.median(ms) for cid, ms in values.items() if kind in cid)
                      for kind in ("airline", "mixed_factors")} for name, values in raw.items()}
    return dict(host=platform.platform(), cpu=args.cpu, wheel_compiler=args.compiler, python=sys.version,
                extension_sha256=hashlib.sha256(Path(_kalos.__file__).read_bytes()).hexdigest(),
                core=pykalos.core_version(), reference=captured["runtime"], threads=threads, warmup=args.warmup,
                samples=args.samples, batch=args.batch, scope="prepared fit, arithmetic mean of four case medians per model",
                summary_ms=summary, samples_ms=raw, agreement=evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu", required=True)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--batch", type=int, default=3)
    args = parser.parse_args()
    result = run(args)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary_ms"], indent=2))
