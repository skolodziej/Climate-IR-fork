"""Daikin remote families."""

from __future__ import annotations

from .profiles import DaikinProfile

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (DaikinProfile,)

__all__ = ["PROFILES", "DaikinProfile"]
