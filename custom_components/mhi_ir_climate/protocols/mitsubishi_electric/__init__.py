"""Mitsubishi Electric remote families."""

from __future__ import annotations

from .profiles import (
    MSCProfile,
    MSYProfile,
    MSZFAProfile,
    MSZFDProfile,
    MSZFEProfile,
    MSZKJProfile,
    SEZKDXXProfile,
)

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (
    MSZFDProfile,
    MSZFEProfile,
    MSZFAProfile,
    MSZKJProfile,
    MSYProfile,
    MSCProfile,
    SEZKDXXProfile,
)

__all__ = [
    "PROFILES",
    "MSCProfile",
    "MSYProfile",
    "MSZFAProfile",
    "MSZFDProfile",
    "MSZFEProfile",
    "MSZKJProfile",
    "SEZKDXXProfile",
]
