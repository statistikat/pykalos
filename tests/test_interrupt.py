"""Exercise interpreter signal delivery during installed native operations."""
import _thread
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest


def interrupted_operation(name):
    import pykalos

    if name == "convolve":
        left, right = [1.] * 100_000, [1.] * 100_000
        def run():
            return pykalos.convolve(left, right)
    else:
        data = [2 + math.sin(i / 12) + .3 * math.cos(i * .71) for i in range(3000)]
        blocks = {k: dict(initial=[0.], fixed=[False]) for k in ("ma", "seasonal_ma")}
        control = dict(eps=1e-12, feps=1e-4, maximum_likelihood=True, unit_root_search=False,
                       corrected_degrees_of_freedom=True, fast_derivatives=True,
                       starting_point="zero", solver="bfgs")
        def run():
            return pykalos.estimate_sarima_fixed(data, period=12, d=1, seasonal_d=1,
                                                blocks=blocks, control=control)

    timer = threading.Timer(.25, _thread.interrupt_main)
    timer.start()
    try:
        run()
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError(f"{name} completed without delivering the interrupt")
    finally:
        timer.cancel()
        timer.join()
    if pykalos.convolve([1., 2.], [1.]) != [1., 2.]:
        raise AssertionError("module could not be reused after the interruption")


class NativeInterrupt(unittest.TestCase):
    def test_caller_receives_interrupt_and_can_reuse_module(self):
        for name in ("convolve", "estimate_sarima_fixed"):
            with self.subTest(operation=name):
                env = dict(os.environ, KALOS_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
                completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), name], timeout=15,
                                           capture_output=True, text=True, env=env)
                self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    interrupted_operation(sys.argv[1])
