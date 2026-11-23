"""Run installed fit routes with no Java executable or loadable VM in use."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def jvm_loaded():
    if sys.platform == "win32":
        get_module = ctypes.windll.kernel32.GetModuleHandleW
        get_module.argtypes = [ctypes.c_wchar_p]
        get_module.restype = ctypes.c_void_p
        return bool(get_module("jvm.dll"))
    if sys.platform == "darwin":
        dyld = ctypes.CDLL(None)
        dyld._dyld_image_count.restype = ctypes.c_uint32
        dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
        dyld._dyld_get_image_name.restype = ctypes.c_char_p
        return any(os.path.basename(dyld._dyld_get_image_name(i) or b"") == b"libjvm.dylib"
                   for i in range(dyld._dyld_image_count()))
    if sys.platform.startswith("linux"):
        return b"/libjvm.so" in Path("/proc/self/maps").read_bytes()
    raise RuntimeError(f"No loaded-JVM check for {sys.platform}")


def run_isolated():
    if shutil.which("java") or shutil.which("javac") or jvm_loaded():
        raise RuntimeError("Java is visible to the isolated wheel test")

    def require_in_process(event, args):
        if event in ("subprocess.Popen", "os.system", "os.posix_spawn"):
            raise RuntimeError(f"The fit attempted to start another process ({event})")

    sys.addaudithook(require_in_process)
    tests = unittest.defaultTestLoader.loadTestsFromNames([
        "test_x13_fixed.FixedFitTest.test_reference_corpora",
        "test_x13_automatic.Test_quick.test_case",
        "test_tramoseats_fit.Rsa0Fit.test_raw_series_oracle",
        "test_tramo_automatic.PublicTr1.test_raw_rsa1_product",
        "test_tramo_automatic.PublicTr3.test_raw_rsa3_product",
    ])
    result = unittest.TextTestRunner(verbosity=1).run(tests)
    if not result.wasSuccessful() or result.skipped or result.testsRun != 5 or jvm_loaded():
        raise RuntimeError("Installed-wheel Java-free numerical qualification failed")


class JavaFreeWheel(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") or sys.platform in ("win32", "darwin"),
                         "loaded-JVM inspection covers the three supported wheel platforms")
    def test_fit_routes_without_java(self):
        script = Path(__file__).resolve()
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "absent-jdk")
            env = os.environ | dict(PATH=directory, JAVA_HOME=missing, JDK_HOME=missing,
                                    JRE_HOME=missing, CLASSPATH="", PYKALOS_X13AUTO_CASES="quick")
            child = subprocess.run([sys.executable, str(script), "--isolated"], env=env, cwd=directory,
                                   text=True, capture_output=True, timeout=180)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


if __name__ == "__main__":
    if sys.argv[1:] == ["--isolated"]:
        run_isolated()
    else:
        unittest.main()
