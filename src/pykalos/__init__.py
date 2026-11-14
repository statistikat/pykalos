"""Minimal Python interface to the pinned Kalos C++ engine."""
from ._kalos import capabilities, convolve, core_version
__all__ = ["capabilities", "convolve", "core_version"]
__version__ = "0.1.0"
