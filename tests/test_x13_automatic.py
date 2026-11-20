"""M4: automatic-preprocessing qualification at the Python boundary.

Runs the pinned 21-H JVM-oracle corpus (vendored schema-2 "evidence"
snapshot, parsed by x13auto_corpus.py exactly as the core's golden generator
projects it) through pykalos.x13_automatic and compares against the pinned
JVM facts with the core contract's tier table - NO relaxation anywhere:

  DECISIONS, bit-exact: final description (status/log/mean/orders), the
  effective mode, variable identities (name/type/position/regeffect),
  differencing decisions, ARMA selections and panel membership, ODM picks
  and the incoming cv, the cascade final-spec remark, the effective-
  observation count.
  BANDED numerics: tmean 1e-3 (21-D trial-fit class), panel BIC2 1e-2,
  observer AICC display pair 1e-5, landing loglik/aicc and regression
  coefficients 2e-3 (refinement basin), ARMA landing coefficients 1e-2
  (G2 basin seam), downstream tables 1e-6 relative.

Case selection: PYKALOS_X13AUTO_CASES (comma-separated corpus ids; default
the outlier-detection-free cases, which the core itself designates as the
cheap tier). Detection-on cases (~230 s each single-process upstream) run
when listed explicitly.
"""
import math
import os
import struct
import unittest

import pykalos
from x13auto_corpus import EVIDENCE, load_corpus, verify_sha256sums

CORPUS = load_corpus()
DEFAULT_CASES = ",".join(sorted(cid for cid, c in CORPUS.items() if not c["outliers"]))
SELECTED = [c for c in os.environ.get("PYKALOS_X13AUTO_CASES", DEFAULT_CASES).split(",") if c]

TYPE_NAMES = {0: "AO", 1: "LS", 2: "TC", 3: "SO"}

# Core contract bands (tests/test_x13_automatic_oracle.cpp at the pin) -
# copied, never widened.
TMEAN_BAND = 1e-3
PANEL_BIC_BAND = 1e-2
DISPLAY_BAND = 1e-5
BASIN_BAND = 2e-3
COEFF_BASIN_BAND = 1e-2
TABLE_BAND = 1e-6


def bits(x):
    return struct.pack(">d", x)


def same_double(a, b):
    return bits(a) == bits(b) or (math.isnan(a) and math.isnan(b))


def rel(a, b):
    return abs(a - b) / abs(b) if b != 0.0 else abs(a - b)


class Scoreboard:
    """Family tally of the oracle test (checks / bad / exact / worst-rel)."""

    def __init__(self):
        self.families = {}

    def tally(self, name, ok, bit=False, dev=0.0, where=""):
        f = self.families.setdefault(name, {"checks": 0, "bad": 0, "exact": 0,
                                            "worst": 0.0, "where": ""})
        f["checks"] += 1
        if bit:
            f["exact"] += 1
        if not ok:
            f["bad"] += 1
        if dev > f["worst"]:
            f["worst"], f["where"] = dev, where

    def bit(self, name, ok, where):
        self.tally(name, ok, bit=ok, dev=0.0 if ok else 1.0, where=where)

    def close(self, name, got, want, band, where):
        if same_double(got, want):
            self.tally(name, True, bit=True, where=where)
            return
        deviation = rel(got, want)
        self.tally(name, math.isfinite(got) and deviation <= band, dev=deviation, where=where)

    def merge_into(self, other):
        for name, f in self.families.items():
            g = other.families.setdefault(name, {"checks": 0, "bad": 0, "exact": 0,
                                                 "worst": 0.0, "where": ""})
            g["checks"] += f["checks"]
            g["bad"] += f["bad"]
            g["exact"] += f["exact"]
            if f["worst"] > g["worst"]:
                g["worst"], g["where"] = f["worst"], f["where"]

    def report(self):
        lines = []
        bad = checks = 0
        for name, f in sorted(self.families.items()):
            lines.append(f"[worst] {name:20s} checks={f['checks']:4d} bad={f['bad']:2d} "
                         f"exact={f['exact']:4d} worst_rel={f['worst']:.3e} at {f['where']}")
            bad += f["bad"]
            checks += f["checks"]
        lines.append(f"[worst] total checks={checks} failures={bad}")
        return "\n".join(lines)

    def assert_clean(self, tc, context):
        bad = sum(f["bad"] for f in self.families.values())
        tc.assertEqual(bad, 0, f"{context}: {self.report()}")


BOARD = Scoreboard()


def tearDownModule():
    print("\n== pykalos M4 boundary scoreboard (measured worsts vs contract bands) ==")
    print(BOARD.report())


# ---- chain projections (mirror the oracle test's helpers) -------------------

def stage_suffix(chain, suffix):
    return [e for e in chain if e["stage"].endswith(suffix)]


def stage_entries(chain, stage):
    return [e for e in chain if e["stage"] == stage]


def odm_entries(chain):
    entries = list(stage_entries(chain, "outliers0"))
    for k in range(1, 100):
        got = stage_entries(chain, f"round{k}.outliers")
        if not got:
            break
        entries.extend(got)
    return entries


def entry_scalar(entry, key):
    for k, v in entry["scalars"]:
        if k == key:
            return v
    return float("nan")


class CorpusShapeTest(unittest.TestCase):
    def test_evidence_sha256sums(self):
        verify_sha256sums(EVIDENCE)

    def test_corpus_complete(self):
        self.assertEqual(len(CORPUS), 13)
        self.assertIn("quick", CORPUS)
        self.assertIn("seas", CORPUS)


class BoundarySurfaceTest(unittest.TestCase):
    """Spec-surface contract: capabilities, defaults, provenance, fail-closed."""

    def test_capabilities_report_the_automatic_entry(self):
        caps = pykalos.capabilities()
        self.assertEqual(caps["primitives"], ("convolve", "x13_automatic"))
        self.assertFalse(caps["fit"])
        auto = caps["automatic"]
        self.assertEqual(auto["sigma_policy_default"], "legacy")
        self.assertTrue(auto["x13_automatic_qualified"])
        self.assertTrue(auto["monthly_only"])
        self.assertTrue(auto["zero_horizon_only"])
        self.assertEqual(auto["frequency"], 12)
        self.assertEqual(auto["modes"],
                         ("additive", "multiplicative", "log_additive", "pseudo_additive"))

    def test_unknown_spec_names_raise_before_the_core(self):
        for kw in ({"mode": "addiitive"}, {"sigma": "hybrid"},
                   {"msr_policy": "fraire"}, {"seasonal": ["s3x7"] * 12},
                   {"outlier_types": ["BA"]}):
            with self.assertRaises(ValueError):
                pykalos.x13_automatic([1.0, 2.0], **kw)

    def test_regression_inputs_are_refused_not_routed(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic([1.0, 2.0], variables=[1.0, 2.0])
        self.assertIn("deferred", str(ctx.exception))

    def _quick_case(self):
        return CORPUS["quick"]

    def test_fail_closed_matrix_statuses_verbatim(self):
        c = self._quick_case()
        values = c["values"]

        def run(**kw):
            return pykalos.x13_automatic(values, start_year=c["first_year"],
                                         start_period=c["first_period"], **kw)

        cases = [
            ({"frequency": 4, "seasonal": ["msr"] * 4},
             "unsupported:x13 automatic fit monthly series only"),
            ({"backcast": 1}, "unsupported:x13 fit requires zero horizons"),
            ({"forecast": 2}, "unsupported:x13 fit requires zero horizons"),
            ({"use_user_variables": True},
             "unsupported:x13 automatic fit defers calendar/easter/TD/user detection (21-I)"),
            ({"use_calendar_detection": True},
             "unsupported:x13 automatic fit defers calendar/easter/TD/user detection (21-I)"),
            ({"automatic_trading_days": True},
             "unsupported:x13 automatic fit defers calendar/easter/TD/user detection (21-I)"),
            ({"outliers": True, "outlier_span": (10, 80)},
             "unsupported:x13 automatic fit spans the full series only"),
        ]
        for kw, want in cases:
            with self.subTest(**kw):
                result = run(**kw)
                self.assertEqual(result["status"], want)
                self.assertFalse(result["available"])
        broken = list(values)
        broken[5] = float("nan")
        result = pykalos.x13_automatic(broken, start_year=c["first_year"],
                                       start_period=c["first_period"])
        self.assertEqual(result["status"],
                         "unsupported:x13 automatic fit requires a complete finite series")
        self.assertFalse(result["available"])

    def test_raw_entry_keeps_the_sigma_policy_explicit(self):
        c = self._quick_case()
        request = dict(pykalos._X13_AUTOMATIC_DEFAULTS)
        request.update({
            "input": c["values"], "frequency": 12, "first_year": c["first_year"],
            "first_period": c["first_period"], "outliers_used": False,
            "outlier_types": list(c["otypes"]), "outlier_span": None,
            "seasonal": ["msr"] * 12, "trend_length": 0,
            "lower_sigma": c["lower_sigma"], "upper_sigma": c["upper_sigma"],
            "msr_policy": "jdplus", "mode": c["mode"], "backcast": 0, "forecast": 0,
        })
        missing = pykalos.x13_automatic_fit(request)  # no "sigma" key at all
        self.assertEqual(missing["status"],
                         "unsupported:x13 fit requires an explicit sigma policy")
        request["sigma"] = None  # explicit none is still unset for the core
        self.assertEqual(pykalos.x13_automatic_fit(request)["status"],
                         "unsupported:x13 fit requires an explicit sigma policy")


class AutomaticOracleTest(unittest.TestCase):
    """Per-case decision-bit + band comparison against the pinned JVM facts."""

    def _run_case(self, cid):
        c = CORPUS[cid]
        result = pykalos.x13_automatic(
            c["values"], frequency=12, start_year=c["first_year"],
            start_period=c["first_period"], mode=c["mode"], sigma="accurate",
            lower_sigma=c["lower_sigma"], upper_sigma=c["upper_sigma"],
            outliers=c["outliers"],
            outlier_types=[TYPE_NAMES[t] for t in c["otypes"]],
            aicc_log_correction=c["aicc_log_correction"], ub1=c["ub1"], ub2=c["ub2"],
            cancel=c["cancel"], tcrate=c["tcrate"], mixed=c["mixed"],
            balanced=c["balanced"], ljung_box_limit=c["ljung_box_limit"],
            reduce_va=c["reduce_va"], outlier_max_round=c["maxiter"])
        return c, result

    def _compare(self, cid):
        b = Scoreboard()
        where = cid
        c, res = self._run_case(cid)
        self.assertEqual(res["sigma_policy_provenance"], "accurate (explicit)")

        # ---- status and final description: bit ----------------------------
        b.bit("model-facts", res["status"] == "available", where + "/status")
        if res["status"] != "available":
            b.merge_into(BOARD)
            self.fail(f"{where}: status {res['status']}")
        exp = c["exp"]
        for key in ("log", "mean"):
            b.bit("model-facts", res[key] == exp[key], f"{where}/{key}")
        orders = (res["p"], res["d"], res["q"], res["bp"], res["bd"], res["bq"])
        want_orders = (exp["p"], exp["d"], exp["q"], exp["bp"], exp["bd"], exp["bq"])
        b.bit("model-facts", orders == want_orders, where + "/orders")
        b.bit("model-facts", res["fit"]["mode_effective"] == c["mode_effective"],
              where + "/mode_effective")
        b.bit("model-facts", res["sigma_policy_provenance"] == "accurate (explicit)",
              where + "/provenance")

        # ---- variables: identity bit, landing coefficients banded ----------
        got_vars = sorted(res["variables"], key=lambda v: (v["position"], v["type"]))
        b.bit("variables", len(got_vars) == exp["nvars"], where + "/nvars")
        for i, (got, want) in enumerate(zip(got_vars, c["vars"])):
            tag = f"{where}/var{i}"
            for key in ("position", "type", "name", "regeffect"):
                b.bit("variables", got[key] == want[key], f"{tag}/{key}")
            if want["row"] < len(c["regcoef"]):
                b.close("landing-coefficients", got["coefficient"],
                        c["regcoef"][want["row"]], BASIN_BAND, tag + "/coef")

        flat = [x for block in res["coefficients"] for x in block]
        b.bit("model-facts", len(flat) == len(c["arma"]), where + "/narma")
        for i, (got, want) in enumerate(zip(flat, c["arma"])):
            b.close("landing-coefficients", got, want, COEFF_BASIN_BAND,
                    f"{where}/arma{i}")

        # ---- landing statistics ---------------------------------------------
        b.bit("landing-stats", res["effective_observations"] == c["neff"],
              where + "/neff")
        b.close("landing-stats", res["log_likelihood"], c["loglik"], BASIN_BAND,
                where + "/loglik")
        b.close("landing-stats", res["aicc"], c["aicc"], BASIN_BAND, where + "/aicc")

        chain = res["chain"]
        evs = c["evs"]

        # ---- kind 1: log-level display pair + preference scalar --------------
        aicc_evs = [e for e in evs if e["kind"] == 1]
        trans = stage_suffix(chain, "transformation")
        b.bit("chain-counts", len(aicc_evs) == len(trans), where + "/aicc-count")
        for i, (ev, entry) in enumerate(zip(aicc_evs, trans)):
            tag = f"{where}/aicc{i}"
            payload = entry["transformation"]
            if payload is None:
                b.bit("display-aicc", False, tag + "/payload")
                continue
            b.close("display-aicc", payload["aicc_log"], ev["d"][0], DISPLAY_BAND,
                    tag + "/logs")
            b.close("display-aicc", payload["aicc_level"], ev["d"][1], DISPLAY_BAND,
                    tag + "/levels")
            b.tally("display-aicc",
                    same_double(c["aicc_log_correction"], ev["d"][2]), bit=True,
                    where=tag + "/pref")

        # ---- kinds 2/3: differencing and arma selections per refine ----------
        diff_evs = [e for e in evs if e["kind"] == 2]
        arma_evs = [e for e in evs if e["kind"] == 3]
        refines = stage_suffix(chain, ".refine")
        b.bit("chain-counts", len(diff_evs) == len(refines), where + "/diff-count")
        b.bit("chain-counts", len(arma_evs) == len(refines), where + "/arma-count")
        for i, (ev, entry) in enumerate(zip(diff_evs, refines)):
            tag = f"{where}/diff{i}"
            refine = entry["refine"]
            got = refine["differencing"] if refine else None
            if got is None:
                b.bit("diff-decisions", False, tag + "/payload")
                continue
            for key, g, w in (("d", got["d"], ev["i"][0]),
                              ("bd", got["seasonal_d"], ev["i"][1]),
                              ("mean", int(got["mean_correction"]), ev["i"][2])):
                b.bit("diff-decisions", g == w, f"{tag}/{key}")
            b.close("diff-tmean", got["t_mean"], ev["d"][0], TMEAN_BAND, tag + "/tmean")
        for i, (ev, entry) in enumerate(zip(arma_evs, refines)):
            tag = f"{where}/arma{i}"
            refine = entry["refine"]
            if refine is None:
                b.bit("arma-decisions", False, tag + "/payload")
                continue
            for key, g, w in (("p", refine["p"], ev["i"][0]), ("q", refine["q"], ev["i"][1]),
                              ("bp", refine["bp"], ev["i"][2]),
                              ("bq", refine["bq"], ev["i"][3])):
                b.bit("arma-decisions", g == w, f"{tag}/sel-{key}")
            panel = refine["preferred_models"]
            b.bit("arma-panel", len(panel) == len(ev["panel"]), tag + "/panel-size")
            for j, (got, (spec, bic)) in enumerate(zip(panel, ev["panel"])):
                ptag = f"{tag}/panel{j}"
                b.bit("arma-panel", (got["p"], got["q"], got["bp"], got["bq"]) == spec,
                      ptag + "/spec")
                b.close("arma-panel", got["bic"], bic, PANEL_BIC_BAND, ptag + "/bic")

        # ---- kind 4: ODM rounds (picks bit, incoming cv bit) -----------------
        odm_evs = [e for e in evs if e["kind"] == 4]
        entries = odm_entries(chain)
        b.bit("chain-counts", len(odm_evs) == len(entries), where + "/odm-count")
        for i, (ev, entry) in enumerate(zip(odm_evs, entries)):
            tag = f"{where}/odm{i}"
            payload = entry["outliers"]
            if payload is None:
                b.bit("odm-decisions", False, tag + "/payload")
                continue
            got = sorted((o["position"], o["type"]) for o in payload["outliers"])
            want = sorted((p, t) for p, t in ev["picks"])
            b.bit("odm-decisions", got == want, tag + "/picks")
            b.tally("odm-decisions", same_double(entry_scalar(entry, "cv"), ev["d"][0]),
                    bit=True, where=tag + "/cv")

        # ---- kind 5: cascade final-spec remark equals the final orders -------
        for ev in (e for e in evs if e["kind"] == 5):
            remark = (res["p"], res["d"], res["q"], res["bp"]) == ev["i"][:4]
            remark = remark and (ev["d"][0], ev["d"][1]) == (res["bd"], res["bq"])
            b.bit("model-facts", remark, where + "/cascade-remark")

        # ---- downstream composition tables -----------------------------------
        for name, key in (("out", "out"), ("d11final", "d11final"), ("e11", "e11")):
            table = res["fit"][key]
            b.bit("tables", len(table) == c["n"], f"{where}/{name}/length")
            for i, (got, want) in enumerate(zip(table, c["tables"][key])):
                b.close("tables", got, want, TABLE_BAND, f"{where}/{name}[{i}]")

        b.merge_into(BOARD)
        b.assert_clean(self, where)


def _make_case_test(cid):
    class Case(AutomaticOracleTest):
        def test_case(self):
            self._compare(cid)
    Case.__name__ = f"AutomaticOracle_{cid}"
    Case.__qualname__ = Case.__name__
    return Case


for _cid in SELECTED:
    if _cid not in CORPUS:
        raise unittest.SkipTest(f"unknown corpus case: {_cid}")
    globals()[f"Test_{_cid}"] = _make_case_test(_cid)
del _cid

if __name__ == "__main__":
    unittest.main()
