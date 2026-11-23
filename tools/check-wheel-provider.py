"""Verify and log the OpenBLAS library used by an installed POSIX test wheel."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path

from pykalos import _kalos, core_version


class DlInfo(ctypes.Structure):
    _fields_ = [
        ("filename", ctypes.c_char_p),
        ("base", ctypes.c_void_p),
        ("symbol", ctypes.c_char_p),
        ("address", ctypes.c_void_p),
    ]


def check_provider(prefix):
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
    parser.add_argument("prefix", type=Path)
    check_provider(parser.parse_args().prefix)
