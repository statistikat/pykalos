"""Verify and log the OpenBLAS library used by an installed test wheel."""
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from pykalos import _kalos, core_version


class DlInfo(ctypes.Structure):
    _fields_ = [
        ("filename", ctypes.c_char_p),
        ("base", ctypes.c_void_p),
        ("symbol", ctypes.c_char_p),
        ("address", ctypes.c_void_p),
    ]


def private_provider(image_path, extension, info):
    if info["provider_linkage"] != "private_static":
        raise RuntimeError("The wheel must include the private static OpenBLAS provider")
    expected = {"DYNAMIC_ARCH", "USE_LOCKING", "SINGLE_THREADED"}
    if not expected.issubset(info["provider_version"].split()):
        raise RuntimeError(f"Unexpected private provider build: {info['provider_version']}")
    for symbol in ("openblas_get_config", "cblas_dgemm", "LAPACKE_dpotrf_work", "dpotrf_"):
        if hasattr(extension, symbol):
            raise RuntimeError(f"The wheel exposes an unqualified numerical symbol: {symbol}")
    if sys.platform == "darwin":
        deps = "\n".join(subprocess.check_output(["otool", "-L", str(image_path)], text=True).splitlines()[1:])
    elif sys.platform == "win32":
        import pefile
        with pefile.PE(str(image_path)) as binary:
            deps = "\n".join(entry.dll.decode() for entry in binary.DIRECTORY_ENTRY_IMPORT)
    else:
        deps = subprocess.check_output(["readelf", "-d", str(image_path)], text=True)
    if "openblas" in deps.lower():
        raise RuntimeError(f"The private extension dynamically loads OpenBLAS: {deps}")
    return image_path


def check_provider(prefix=None):
    root = Path(__file__).resolve().parents[1]
    core = json.loads((root / "core.lock.json").read_text())
    pin = json.loads((root / "vendor/kalos/dependencies/openblas.lock.json").read_text())
    info = core_version()
    if info["commit"] != core["commit"] or info["blas_integer_bits"] != 32:
        raise RuntimeError(f"Unexpected core revision or integer ABI: {info}")
    if info["provider_version"].split()[:2] != ["OpenBLAS", pin["version"]]:
        raise RuntimeError(f"Unexpected OpenBLAS version: {info['provider_version']}")

    # Resolve the symbol through the installed extension's dependencies. A
    # separately opened library could give a convincing fingerprint for the
    # wrong provider when two OpenBLAS installations coexist.
    extension = ctypes.CDLL(_kalos.__file__)
    if prefix is None:
        provider = private_provider(Path(_kalos.__file__).resolve(), extension, info)
    else:
        get_config = extension.openblas_get_config
        get_config.restype = ctypes.c_char_p
        if get_config().decode() != info["provider_version"]:
            raise RuntimeError("The mapped provider disagrees with the core configuration")
        dladdr = ctypes.CDLL(None).dladdr
        dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
        dladdr.restype = ctypes.c_int
        image = DlInfo()
        if not dladdr(get_config, ctypes.byref(image)) or not image.filename:
            raise RuntimeError("Unable to locate the mapped OpenBLAS provider")
        provider = Path(os.fsdecode(image.filename)).resolve(strict=True)
        if not provider.is_relative_to(prefix.resolve(strict=True)):
            raise RuntimeError(f"Wheel loaded {provider} outside {prefix}")
    print(json.dumps({
        **info, "library": str(provider),
        "library_sha256": hashlib.sha256(provider.read_bytes()).hexdigest(),
        "source_archive_sha256": pin["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("prefix", type=Path, nargs="?")
    mode.add_argument("--bundled", action="store_true", help="verify OpenBLAS is private to the extension")
    check_provider(parser.parse_args().prefix)
