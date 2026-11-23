"""Compare installed pykalos and a checksummed JD+ JVM on two original monthly series."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import struct
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = ROOT / "vendor/kalos-evidence/native/tramo-seats-bridge"
CORPUS = EVIDENCE / "rsa0-x86_64.txt"
CASES = ("fit_tr0_air", "fit_multi")


def decode(tokens):
    return [struct.unpack(">d", bytes.fromhex(token))[0] for token in tokens]


def fixtures():
    cases = {cid: {} for cid in CASES}
    for path in (CORPUS, EVIDENCE / "rsa0-forecast-errors-x86_64.txt"):
        for line in path.read_text().splitlines():
            fields = line.split()
            if fields[0] == "case":
                case = cases.get(fields[1])
            elif case is not None:
                if fields[0] == "input":
                    case["request"] = dict(
                        start_year=int(fields[1]),
                        start_month=int(fields[2]),
                        series=decode(fields[4:]),
                    )
                elif fields[:3] == ["merged", "SeasonallyAdjusted", "Value"]:
                    case["adjusted"] = fields[6:]
                elif fields[0] == "y_ef":
                    case["errors"] = fields[4:]
    return cases


def native_worker(warmup, samples, batch):
    import pykalos

    cases = fixtures()
    for _ in range(warmup):
        for case in cases.values():
            pykalos.tramoseats_fit(**case["request"])
    for i in range(samples):
        for cid, case in cases.items():
            start = time.perf_counter_ns()
            for _ in range(batch):
                fit = pykalos.tramoseats_fit(**case["request"])
                adjusted, errors = fit["finalSA"], fit["series_forecast_stdev"]
            elapsed = time.perf_counter_ns() - start
            print("sample", cid, elapsed)
            if i == samples - 1:
                rows = fit["initial"] + fit["final"] + fit["merged"]
                print("rows", cid, len(rows), sum(len(row["values"]) for row in rows))
                for name, values in (("adjusted", adjusted), ("errors", errors)):
                    print("values", cid, name, *(struct.pack(">d", x).hex() for x in values))


def verify(captured, expected, require_exact):
    if len(captured) != len(expected):
        raise ValueError("timed result has a different length from the oracle")
    actual, reference = decode(captured), decode(expected)
    if not all(map(math.isfinite, actual)):
        raise ValueError("non-finite timed result")
    worst = max(abs(a - b) for a, b in zip(actual, reference))
    equal = sum(a == b for a, b in zip(captured, expected))
    if require_exact and equal != len(captured):
        raise ValueError("timed adjusted series differs from the qualified x86-64 oracle")
    return dict(n=len(captured), exact=equal, max_abs=worst)


def benchmark(args):
    import pykalos
    from pykalos import _kalos

    cases = fixtures()
    reference = json.loads((EVIDENCE / "reference.json").read_text())
    jars = []
    for name, digest in reference["jars"].items():
        jar = next((root / name for root in args.jar_dir if (root / name).is_file()), None)
        if jar is None or hashlib.sha256(jar.read_bytes()).hexdigest() != digest:
            raise ValueError(f"missing or incorrect pinned JAR: {name}")
        jars.append(str(jar))
    java, javac = (args.jdk / "bin" / exe for exe in ("java", "javac"))
    settings = subprocess.check_output(
        [java, "-XshowSettings:properties", "-version"], stderr=subprocess.STDOUT, text=True
    )
    properties = dict(
        line.lstrip().split(" = ", 1) for line in settings.splitlines() if " = " in line
    )
    aliases = {"aarch64": "arm64", "amd64": "x86_64"}
    arch = aliases.get(properties["os.arch"], properties["os.arch"])
    host_arch = platform.machine().lower()
    if arch != aliases.get(host_arch, host_arch):
        raise ValueError("use a native JVM on the same architecture as the installed wheel")
    if properties["java.version"] != reference["java_version"]:
        raise ValueError("the JVM version differs from the pinned reference")
    core = pykalos.core_version()
    if core["commit"] != json.loads((ROOT / "core.lock.json").read_text())["commit"]:
        raise ValueError("installed wheel differs from the checkout's core pin")
    env = os.environ | dict(
        KALOS_NUM_THREADS=str(args.threads),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS=str(args.threads),
    )
    params = list(map(str, (args.warmup, args.samples, args.batch)))
    results = {
        engine: {cid: dict(ms=[], oracle={}) for cid in CASES} for engine in ("python", "java")
    }
    vm_options = [
        f"-XX:ActiveProcessorCount={args.threads}",
        f"-Djava.util.concurrent.ForkJoinPool.common.parallelism={args.threads}",
        "-XX:+UnlockDiagnosticVMOptions",
        "-XX:DisableIntrinsic=_dexp,_dlog",
    ]
    with tempfile.TemporaryDirectory() as classes:
        subprocess.run(
            [javac, "-cp", os.pathsep.join(jars), "-d", classes, HERE / "Rsa0Timing.java"],
            check=True,
        )
        commands = dict(
            java=[
                java,
                *vm_options,
                "-cp",
                os.pathsep.join([classes, *jars]),
                "Rsa0Timing",
                CORPUS,
                *params,
            ],
            python=[sys.executable, __file__, "--worker", *params],
        )
        for repetition in range(args.processes):
            for engine in (("python", "java") if repetition % 2 == 0 else ("java", "python")):
                lines = subprocess.check_output(commands[engine], env=env, text=True).splitlines()
                for line in lines:
                    kind, cid, *fields = line.split()
                    record = results[engine][cid]
                    if kind == "sample":
                        record["ms"].append(int(fields[0]) / (1e6 * args.batch))
                    elif kind == "rows":
                        shape = [int(x) for x in fields]
                        if record.setdefault("materialized_rows_and_values", shape) != shape:
                            raise ValueError(
                                "component shapes changed across independent processes"
                            )
                    elif kind == "values":
                        field, *captured = fields
                        expected = cases[cid][field]
                        summary = verify(captured, expected, field == "adjusted")
                        if field == "errors" and any(
                            abs(a - b) > 2e-8 * (1 + abs(b))
                            for a, b in zip(decode(captured), decode(expected))
                        ):
                            raise ValueError(
                                "timed forecast uncertainty exceeds the frozen covariance budget"
                            )
                        if record["oracle"].setdefault(field, summary) != summary:
                            raise ValueError(
                                "oracle comparison changed across independent processes"
                            )
                    else:
                        raise ValueError(f"unexpected benchmark record: {kind}")
    for tables in results.values():
        for record in tables.values():
            if len(record["ms"]) != args.samples * args.processes or set(record["oracle"]) != {
                "adjusted",
                "errors",
            }:
                raise ValueError("incomplete benchmark output")
            record["median_ms"] = statistics.median(record["ms"])
    for cid in CASES:
        if (
            results["java"][cid]["materialized_rows_and_values"]
            != results["python"][cid]["materialized_rows_and_values"]
        ):
            raise ValueError("the timed calls returned different component payload sizes")
    print(
        json.dumps(
            dict(
                host=platform.platform(),
                host_cpu=args.host_cpu,
                wheel_compiler=args.wheel_compiler,
                extension_sha256=hashlib.sha256(Path(_kalos.__file__).read_bytes()).hexdigest(),
                python=sys.version.splitlines()[0],
                core=core,
                java_runtime=properties["java.runtime.version"],
                java_arch=arch,
                jvm_flags=vm_options,
                kalos_threads=args.threads,
                openblas_threads=1,
                warmup=args.warmup,
                samples_per_process=args.samples,
                fresh_processes=args.processes,
                fits_per_sample=args.batch,
                results=results,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        native_worker(*map(int, sys.argv[2:]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--host-cpu", help="CPU model for the output record")
        parser.add_argument("--wheel-compiler", help="C++ compiler used to build the timed wheel")
        parser.add_argument("--jdk", required=True, type=Path)
        parser.add_argument("--jar-dir", required=True, action="append", type=Path)
        for name, default in (
            ("warmup", 20),
            ("samples", 7),
            ("batch", 5),
            ("processes", 4),
            ("threads", 1),
        ):
            parser.add_argument("--" + name, type=int, default=default)
        options = parser.parse_args()
        if (
            min(options.warmup, options.samples, options.batch, options.processes, options.threads)
            < 1
        ):
            parser.error("counts must be positive")
        benchmark(options)
