"""21-H.4: positive-horizon qualification of the automatic route at the boundary.

Replays the item 21-H.4 JVM horizon capture (vendored "evidence" snapshot
vendor/kalos-evidence/native/x13-horizon, provenance ["evidence"], pinned in
core.lock.json at core f500162a3be1539803566f9bc8f071e0deb4f66b; SHA256SUMS.csv
pins cases.csv 2e186f15..., inputs.csv 8b6f8889..., oracle-facts.csv
ed80b837..., metadata.R a353ca5d...) through pykalos.x13_automatic with the
captured X-11 horizons and compares against the JVM facts at the tiers the
core itself claimed - NO relaxation anywhere.

Contracts (core repo at the pin; docs are not part of the vendored core
section, so the tiers are transcribed with citation from upstream's own
acceptance encoding, tests/jvm_x13_automatic_horizon.h kCases band[] and
tests/test_x13_automatic_horizon.cpp):
  docs/contracts/arima-forecasts-contract.md  ("Acceptance tiers": decisions
      BIT-exact; a1, d18 and the d18a/d18b slices bit-exact claims; every
      other table carries the measured band inherited from the landing-
      coefficient basin drift)
  docs/contracts/x13-automatic-pipeline-contract.md ("Horizon extension
      (21-H.4)": horizons feed the downstream composition ONLY; estimation,
      the decision chain and landing coefficients are horizon-invariant)

Boundary scope: the binding exposes the three qualified composition tables
(out, d11final, e11) - the bit-tier tables a1/d18/d18a/d18b stay inside the
C++ result and are qualified upstream, not here. Everything the boundary DOES
expose is pinned: decisions BIT (status, final description, mode_effective,
variable identities, neff, horizon echo, table lengths) and numerics at the
transcribed upstream bands (HZ_BANDS below, copied never widened). Landing
coefficients and loglik/aicc reuse the existing zero-horizon contract bands
(1e-2 / 2e-3): the horizon capture's landing facts are, per the pipeline
contract, byte-identical to the zero-horizon oracle captures, so the same
measured basins apply verbatim.

Case selection: PYKALOS_X13HZ_CASES (comma-separated capture ids; default the
outlier-detection-free cases - quick_h6 - cheap tier). Detection-on captures
(ao_b3, multi_b3h6, so_h6, ~230 s each upstream) run when listed explicitly,
same envelope as the zero-horizon oracle gate.
"""
import os
import unittest

import pykalos
from x13auto_corpus import HORIZON_EVIDENCE, load_horizon_corpus, verify_sha256sums
from test_x13_automatic import (BASIN_BAND, COEFF_BASIN_BAND, Scoreboard,
                                TYPE_NAMES)

HZCORPUS = load_horizon_corpus()
DEFAULT_CASES = ",".join(sorted(cid for cid, c in HZCORPUS.items() if not c["outliers"]))
SELECTED = [c for c in os.environ.get("PYKALOS_X13HZ_CASES", DEFAULT_CASES).split(",") if c]

# Upstream acceptance bands for the boundary-exposed tables, transcribed
# from tests/jvm_x13_automatic_horizon.h kCases at f500162 (0 would be a
# bit claim; none of the exposed tables carries one). Never widened.
HZ_BANDS = {
    "quick_h6":   {"out": 2.0e-06, "d11final": 5.0e-07, "e11": 5.0e-07},
    "ao_b3":      {"out": 5.0e-06, "d11final": 5.0e-07, "e11": 1.0e-06},
    "multi_b3h6": {"out": 1.0e-05, "d11final": 2.0e-06, "e11": 5.0e-06},
    "so_h6":      {"out": 2.0e-05, "d11final": 5.0e-06, "e11": 5.0e-06},
}

BOARD = Scoreboard()


def tearDownModule():
    print("\n== pykalos 21-H.4 horizon scoreboard (measured worsts vs upstream bands) ==")
    print(BOARD.report())


class HorizonShapeTest(unittest.TestCase):
    def test_horizon_evidence_sha256sums(self):
        verify_sha256sums(HORIZON_EVIDENCE)

    def test_horizon_corpus_complete(self):
        self.assertEqual(sorted(HZCORPUS),
                         ["ao_b3", "multi_b3h6", "quick_h6", "so_h6"])
        self.assertEqual(HZCORPUS["multi_b3h6"]["bc"], 3)
        self.assertEqual(HZCORPUS["multi_b3h6"]["fc"], 6)


class HorizonQualificationTest(unittest.TestCase):
    """Per-case JVM horizon replay: bit decisions + transcribed bands."""

    def _compare(self, cid):
        b = Scoreboard()
        where = cid
        c = HZCORPUS[cid]
        result = pykalos.x13_automatic(
            c["values"], frequency=12, start_year=c["first_year"],
            start_period=c["first_period"], mode=c["mode"], sigma="accurate",
            lower_sigma=c["lower_sigma"], upper_sigma=c["upper_sigma"],
            outliers=c["outliers"],
            outlier_types=[TYPE_NAMES[t] for t in c["otypes"]],
            aicc_log_correction=c["aicc_log_correction"], ub1=c["ub1"],
            ub2=c["ub2"], cancel=c["cancel"], tcrate=c["tcrate"],
            mixed=c["mixed"], balanced=c["balanced"],
            ljung_box_limit=c["ljung_box_limit"], reduce_va=c["reduce_va"],
            outlier_max_round=c["maxiter"],
            backcast=c["bc"], forecast=c["fc"])
        res = result
        self.assertEqual(res["sigma_policy_provenance"], "accurate (explicit)")

        # ---- status, final description, horizon echo: bit ------------------
        b.bit("hz/status", res["status"] == "available", where + "/status")
        if res["status"] != "available":
            b.merge_into(BOARD)
            self.fail(f"{where}: status {res['status']}")
        exp = c["exp"]
        for key in ("log", "mean"):
            b.bit("hz/decisions", res[key] == exp[key], f"{where}/{key}")
        orders = (res["p"], res["d"], res["q"], res["bp"], res["bd"], res["bq"])
        want = (exp["p"], exp["d"], exp["q"], exp["bp"], exp["bd"], exp["bq"])
        b.bit("hz/decisions", orders == want, where + "/orders")
        b.bit("hz/decisions", res["fit"]["mode_effective"] == c["mode_effective"],
              where + "/mode_effective")
        b.bit("hz/echo", (res["fit"]["backcast"], res["fit"]["forecast"]) ==
              (c["bc"], c["fc"]), where + "/horizon-echo")

        # ---- variables: identity bit, landing coefficients banded ----------
        got_vars = sorted(res["variables"], key=lambda v: (v["position"], v["type"]))
        b.bit("hz/variables", len(got_vars) == exp["nvars"], where + "/nvars")
        for i, (got, wantv) in enumerate(zip(got_vars, c["vars"])):
            tag = f"{where}/var{i}"
            for key in ("position", "type", "name", "regeffect"):
                b.bit("hz/variables", got[key] == wantv[key], f"{tag}/{key}")
            if wantv["row"] < len(c["regcoef"]):
                b.close("hz/landing-coefficients", got["coefficient"],
                        c["regcoef"][wantv["row"]], BASIN_BAND, tag + "/coef")
        flat = [x for block in res["coefficients"] for x in block]
        b.bit("hz/decisions", len(flat) == len(c["arma"]), where + "/narma")
        for i, (got, wantv) in enumerate(zip(flat, c["arma"])):
            b.close("hz/landing-coefficients", got, wantv, COEFF_BASIN_BAND,
                    f"{where}/arma{i}")

        # ---- landing statistics (horizon-invariant upstream) ---------------
        b.bit("hz/landing-stats", res["effective_observations"] == c["neff"],
              where + "/neff")
        b.close("hz/landing-stats", res["log_likelihood"], c["loglik"],
                BASIN_BAND, where + "/loglik")
        b.close("hz/landing-stats", res["aicc"], c["aicc"], BASIN_BAND,
                where + "/aicc")

        # ---- extended composition: the three boundary-exposed tables -------
        bands = HZ_BANDS[cid]
        lengths = {"out": c["n"] + c["bc"] + c["fc"],
                   "d11final": c["n"], "e11": c["n"]}
        for name in ("out", "d11final", "e11"):
            table = res["fit"][name]
            b.bit("hz/lengths", len(table) == lengths[name],
                  f"{where}/{name}/length")
            b.bit("hz/lengths", len(c["tables"][name]) == lengths[name],
                  f"{where}/{name}/capture-length")
            for i, (got, wantv) in enumerate(zip(table, c["tables"][name])):
                b.close(f"hz/{name}", got, wantv, bands[name],
                        f"{where}/{name}[{i}]")

        b.merge_into(BOARD)
        b.assert_clean(self, where)


def _make_case_test(cid):
    class Case(HorizonQualificationTest):
        def test_case(self):
            self._compare(cid)
    Case.__name__ = f"HorizonQualification_{cid}"
    Case.__qualname__ = Case.__name__
    return Case


for _cid in SELECTED:
    if _cid not in HZCORPUS:
        raise unittest.SkipTest(f"unknown horizon case: {_cid}")
    globals()[f"Test_hz_{_cid}"] = _make_case_test(cid=_cid)
del _cid

if __name__ == "__main__":
    unittest.main()
