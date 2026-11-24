"""Run installed fit routes without Java, R or a child process."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def external_runtime_loaded():
    if sys.platform == "win32":
        get_module = ctypes.windll.kernel32.GetModuleHandleW
        get_module.argtypes = [ctypes.c_wchar_p]
        get_module.restype = ctypes.c_void_p
        return any(get_module(name) for name in ("jvm.dll", "R.dll"))
    if sys.platform == "darwin":
        dyld = ctypes.CDLL(None)
        dyld._dyld_image_count.restype = ctypes.c_uint32
        dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
        dyld._dyld_get_image_name.restype = ctypes.c_char_p
        for i in range(dyld._dyld_image_count()):
            path = dyld._dyld_get_image_name(i) or b""
            if b"/R.framework/" in path or os.path.basename(path) in (b"libjvm.dylib", b"libR.dylib"):
                return True
        return False
    if sys.platform.startswith("linux"):
        maps = Path("/proc/self/maps").read_bytes()
        return any(name in maps for name in (b"/libjvm.so", b"/libR.so"))
    raise RuntimeError(f"No loaded-runtime check for {sys.platform}")


def run_isolated():
    if any(shutil.which(name) for name in ("java", "javac", "R", "Rscript")) or external_runtime_loaded():
        raise RuntimeError("An external runtime is visible to the isolated wheel test")

    def require_in_process(event, args):
        if event in ("subprocess.Popen", "os.system", "os.posix_spawn"):
            raise RuntimeError(f"The fit attempted to start another process ({event})")

    sys.addaudithook(require_in_process)
    names = [
        "test_x13_fixed.FixedFitTest.test_reference_corpora",
        "test_x13_automatic.Test_quick.test_case",
        "test_tramoseats_fit.Rsa0Fit.test_raw_series_oracle",
        "test_tramo_automatic.PublicTr1.test_raw_rsa1_product",
        "test_tramo_automatic.PublicTr3.test_raw_rsa3_product",
        "test_tramo_automatic.PublicTrFull.test_stock_calendar_preprocessing_and_products",
        "test_x13_estimated.StockX13.test_public_rsa0_model_and_products",
        "test_x13_estimated.StockX13.test_public_rsa1_model_and_products",
        "test_x13_estimated.StockX13.test_public_rsa2c_model_and_products",
    ]
    tests = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=1).run(tests)
    if not result.wasSuccessful() or result.skipped or result.testsRun != len(names) or external_runtime_loaded():
        raise RuntimeError("Installed-wheel runtime-independent numerical qualification failed")


class JavaFreeWheel(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") or sys.platform in ("win32", "darwin"),
                         "loaded-JVM inspection covers the three supported wheel platforms")
    def test_fit_routes_without_java(self):
        script = Path(__file__).resolve()
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "absent-jdk")
            env = os.environ | dict(PATH=directory, JAVA_HOME=missing, JDK_HOME=missing,
                                    JRE_HOME=missing, R_HOME=str(Path(directory) / "absent-R"), CLASSPATH="", PYKALOS_X13AUTO_CASES="quick")
            child = subprocess.run([sys.executable, str(script), "--isolated"], env=env, cwd=directory,
                                   text=True, capture_output=True, timeout=360)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


if __name__ == "__main__":
    if sys.argv[1:] == ["--isolated"]:
        run_isolated()
    else:
        unittest.main()
