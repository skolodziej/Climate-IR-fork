"""Mitsubishi Heavy Industries remote families."""

from __future__ import annotations

from .profiles import (
    FDProfile,
    ZEAProfile,
    ZJProfile,
    ZMPProfile,
    ZSAProfile,
)

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (
    ZSAProfile,
    FDProfile,
    ZJProfile,
    ZMPProfile,
    ZEAProfile,
)

__all__ = [
    "PROFILES",
    "FDProfile",
    "ZEAProfile",
    "ZJProfile",
    "ZMPProfile",
    "ZSAProfile",
]
