"""Reader for the pinned 21-H JVM-oracle corpus vendored by sync-core.py.

Parses vendor/kalos-evidence/native/x13-automatic (schema-2 "evidence"
snapshot) into per-case dicts. The projections follow the core's own golden
generator (upstream tools/gen_x13_automatic_golden.py at the pinned commit)
so the Python boundary compares against exactly the values the C++ oracle
replays: request mirrors from the `req` fact echo (ub1/ub2 inverted into
MODULE space), decision events projected onto kinds 1-5, expected final
descriptions from cases.csv, variable identities from the `var` facts,
landing statistics/coefficients from stats/arma/regcoef, and the three
qualified downstream tables (out, d11final, e11).
"""
import csv
import hashlib
import re
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / "vendor" / "kalos-evidence" / "native" / "x13-automatic"

MODE_NAME = {"Undefined": "undefined", "Multiplicative": "multiplicative",
             "LogAdditive": "log_additive", "PseudoAdditive": "pseudo_additive",
             "Additive": "additive"}
MODE_EXPECTED = {"Undefined": "additive", "Multiplicative": "multiplicative",
                 "LogAdditive": "log_additive", "PseudoAdditive": "pseudo_additive",
                 "Additive": "additive"}
TYPE = {"AO": 0, "LS": 1, "TC": 2, "SO": 3}
SLOW_CASES = set()  # outlier-detection-on cases, filled by load_corpus()


def reals(field, sep=";"):
    return [float(t) for t in field.split(sep) if t]


def _parse_pair4(s, at):
    m = re.match(r"\((-?\d+),(-?\d+)\)\((-?\d+),(-?\d+)\)", s[at:])
    assert m, s
    return tuple(int(g) for g in m.groups()), at + m.end()


def _parse_events(rows):
    """Project the observer stream onto decision kinds (generator parity)."""
    evs = []
    in_full = False
    full_depth = None
    for r in rows:
        d, kind, msg = r["detail"], r["kind"], r["msg"]
        if kind == "push" and msg == "full estimation":
            in_full, full_depth = True, int(r["depth"])
            continue
        if kind == "pop" and in_full and int(r["depth"]) == full_depth:
            in_full = False
        if d.startswith("obj AICC on logs="):
            logs = re.search(r"logs=([-+0-9.eE]+)", d).group(1)
            levels = re.search(r"levels=([-+0-9.eE]+)", d).group(1)
            pref = re.search(r"preference\)=([-+0-9.eE]+)", d).group(1)
            evs.append(dict(kind=1, i=(0, 0, 0, 0),
                            d=(float(logs), float(levels), float(pref)),
                            panel=[], picks=[]))
        elif d.startswith("diff d="):
            m = re.match(r"diff d=(\d+) bd=(\d+) mean=(true|false) tmean=(\S+)", d)
            assert m, d
            evs.append(dict(kind=2, i=(int(m.group(1)), int(m.group(2)),
                                       1 if m.group(3) == "true" else 0, 0),
                            d=(float(m.group(4)), 0.0, 0.0), panel=[], picks=[]))
        elif d.startswith("arma sel="):
            sel, at = _parse_pair4(d, d.index("sel=") + 4)
            panel = []
            while True:
                k = d.find("[", at)
                if k < 0:
                    break
                j = d.find("]", k)
                spec, col = _parse_pair4(d, k + 1)
                panel.append((spec, float(d[col + 1:j])))
                at = j
            evs.append(dict(kind=3, i=sel, d=(0.0, 0.0, 0.0), panel=panel, picks=[]))
        elif d.startswith("odm "):
            head = d[4:]
            types = head[:head.index(" ")]
            names = [t for t in types.split(",") if t]
            picks = [(int(a), TYPE[names[int(b)]]) for a, b in
                     re.findall(r"\[(\d+);(\d+)\]", d)]
            va = d.split()[-1]
            tt = tuple(sorted(TYPE[t] for t in types.split(",") if t))
            evs.append(dict(kind=4, i=tt, d=(float(va), 0.0, 0.0),
                            panel=[], picks=picks))
        elif in_full and kind == "info" and d.startswith("obj ("):
            m = re.match(r"obj \((-?\d+),(-?\d+),(-?\d+)\)\((-?\d+),(-?\d+),(-?\d+)\)", d)
            assert m, d
            o = [int(g) for g in m.groups()]
            evs.append(dict(kind=5, i=(o[0], o[1], o[2], o[3]), d=(o[4], o[5], 0),
                            panel=[], picks=[]))
    return evs


def _parse_var(row):
    toks = row.split()
    ami, regeff = toks[-2], toks[-1]
    return " ".join(toks[1:-2]), ami, regeff


def load_corpus(corpus_dir=EVIDENCE):
    def read_csv(name):
        with open(corpus_dir / name, newline="") as f:
            return list(csv.DictReader(f))

    cases = read_csv("cases.csv")
    inputs, events, facts = {}, {}, {}
    for r in read_csv("inputs.csv"):
        line = r["line"]
        inputs.setdefault(r["id"], {})[line.split(" ", 1)[0]] = line.split(" ", 1)[1]
    for r in read_csv("oracle-events.csv"):
        events.setdefault(r["id"], []).append(r)
    for r in read_csv("oracle-facts.csv"):
        facts.setdefault(r["id"], []).append((r["key"], r["value"]))

    def fact(cid, key):
        for k, v in facts[cid]:
            if k == key:
                return v
        return ""

    def facts_of(cid, key):
        return [v for k, v in facts[cid] if k == key]

    out = {}
    for case in cases:
        cid = case["id"]
        assert case["status"] == "ok", cid
        req_line = fact(cid, "req").split()
        req = dict(zip(req_line[0::2], req_line[1::2]))
        year, period = (int(x) for x in req["start"].split(":"))
        inp = inputs[cid]
        assert inp.get("id", cid) == cid
        values = reals(inp["values"])
        assert len(values) == int(req["n"]) == int(case["n"]), cid
        sigma = req["sigma"].split(";")
        st = re.match(r"nobs=(\d+) neff=(\d+) npar=(\d+) loglik=(\S+) aicc=(\S+)",
                      fact(cid, "stats"))
        assert st, cid
        oracle_vars = [_parse_var(row) for row in facts_of(cid, "var")]
        ami = [(n, re_, int(row.split()[0]))
               for (n, a, re_), row in zip(oracle_vars, facts_of(cid, "var"))
               if a == "x13"]
        out[cid] = {
            "id": cid,
            "n": len(values),
            "values": values,
            "first_year": year, "first_period": period,
            "mode": MODE_NAME[req["mode"]],
            "mode_effective": MODE_EXPECTED[case["mode_effective"]],
            "outliers": req["outliers"] == "on",
            "otypes": sorted(TYPE[t] for t in req["otypes"].split(",") if t),
            "maxiter": int(req["maxiter"]),
            "mixed": req["mixed"] == "true",
            "balanced": req["balanced"] == "true",
            "aicc_log_correction": float(req["aicdiff"]),
            "ub1": 1.0 / float(req["ub1"]),   # module-space reciprocals
            "ub2": 1.0 / float(req["ub2"]),
            "cancel": float(req["cancel"]),
            "tcrate": float(req["tcrate"]),
            "reduce_va": float(req["predcv"]),
            "ljung_box_limit": float(req["lblimit"]),
            "lower_sigma": float(sigma[0]), "upper_sigma": float(sigma[1]),
            # expectations
            "exp": {
                "log": fact(cid, "log") == "true",
                "mean": fact(cid, "mean") == "true",
                "orders": tuple(int(x) for x in fact(cid, "orders").split()),
                "p": int(case["p"]), "d": int(case["d"]), "q": int(case["q"]),
                "bp": int(case["bp"]), "bd": int(case["bd"]), "bq": int(case["bq"]),
                "nvars": len(ami),
            },
            "vars": sorted(
                ({"name": n, "regeffect": ("" if r == "-" else r),
                  "row": row,
                  "position": (int(n.split("(")[1].split(")")[0][:4]) - year) * 12
                              + int(n.split("(")[1].split(")")[0][5:7]) - period,
                  "type": TYPE[n[:2]]}
                 for n, r, row in ami),
                key=lambda v: (v["position"], v["type"])),
            "regcoef": reals(fact(cid, "regcoef")),
            "arma": reals(fact(cid, "arma")),
            "neff": int(st.group(2)),
            "loglik": float(st.group(4)), "aicc": float(st.group(5)),
            "tables": {"out": reals(fact(cid, "out")),
                       "d11final": reals(fact(cid, "d11final")),
                       "e11": reals(fact(cid, "e11"))},
            "evs": _parse_events(events[cid]),
        }
    SLOW_CASES.update(cid for cid, c in out.items() if c["outliers"])
    return out


def verify_sha256sums(corpus_dir=EVIDENCE):
    """Every file listed in the vendored SHA256SUMS.csv hashes to its pin."""
    with open(corpus_dir / "SHA256SUMS.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "SHA256SUMS.csv is empty"
    for row in rows:
        digest = hashlib.sha256((corpus_dir / row["file"]).read_bytes()).hexdigest()
        assert digest == row["sha256"], f"evidence drift: {row['file']}"
