"""Compare two installed wheels on the same fixed-order cases and host load.

Generate the reference with `Rscript --vanilla fixed_order_reference.R
/path/to/kalos reference.json 1 1 1`. Install each wheel in its own directory
using pip --target. Supply the reference, both installations and an output
file. Set the four single-thread environment variables used by fixed_order.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


def sample(reference, case):
    from fixed_order import prepare, verify
    import pykalos
    from pykalos import _kalos

    ref = json.loads(reference.read_text())
    request, jacobian = prepare(ref["inputs"][case])
    pykalos.estimate_sarima_fixed(**request)
    cpu, wall = time.process_time_ns(), time.perf_counter_ns()
    fit = pykalos.estimate_sarima_fixed(**request)
    wall_ms = (time.perf_counter_ns() - wall) / 1e6
    cpu_ms = (time.process_time_ns() - cpu) / 1e6
    for method in ("x13", "tramo"):
        verify(fit, jacobian, request["blocks"], ref[method]["expected"][case])
    return dict(wall_ms=wall_ms, cpu_ms=cpu_ms, core=pykalos.core_version()["commit"],
                extension_sha256=hashlib.sha256(Path(_kalos.__file__).read_bytes()).hexdigest())


def compare(reference, previous, current, output, rounds):
    if rounds < 1:
        raise ValueError("rounds must be positive")
    threads = {k: os.environ.get(k) for k in ("KALOS_NUM_THREADS", "OPENBLAS_NUM_THREADS",
               "OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
    if set(threads.values()) != {"1"}:
        raise ValueError("set all four thread variables to 1")
    captured = json.loads(reference.read_text())
    cases = captured["inputs"]
    samples = {wheel: {case: [] for case in cases} for wheel in ("previous", "current")}
    identities = {}
    wheels = [("previous", previous), ("current", current)]
    for i in range(rounds):
        for j, case in enumerate(cases):
            for label, path in (wheels if (i + j) % 2 == 0 else reversed(wheels)):
                cmd = [sys.executable, Path(__file__).resolve(), "--sample", reference, case]
                result = json.loads(subprocess.check_output(cmd, env=os.environ | {"PYTHONPATH": str(path.resolve())}))
                identity = {k: result.pop(k) for k in ("core", "extension_sha256")}
                if identities.setdefault(label, identity) != identity:
                    raise RuntimeError("installed binary changed during the run")
                samples[label][case].append(result)
    if identities["previous"]["extension_sha256"] == identities["current"]["extension_sha256"]:
        raise ValueError("both installations loaded the same extension")
    summary = {}
    for label, data in samples.items():
        summary[label] = {}
        for kind in ("airline", "mixed_factors"):
            matching = [rows for case, rows in data.items() if kind in case]
            by_metric = {}
            for metric in ("cpu_ms", "wall_ms"):
                medians = [statistics.median(row[metric] for row in rows) for rows in matching]
                by_metric[metric] = statistics.mean(medians)
            summary[label][kind] = by_metric
    report = dict(wheels=identities, threads=threads, rounds=rounds, reference=captured["runtime"],
                  sampling="one warmup then one timed fit per process, alternating the first wheel by case and round",
                  summary=summary, samples=samples)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--sample"]:
        print(json.dumps(sample(Path(sys.argv[2]), sys.argv[3])))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        for name in ("reference", "previous", "current", "output"):
            parser.add_argument(name, type=Path)
        parser.add_argument("--rounds", type=int, default=5)
        compare(**vars(parser.parse_args()))
