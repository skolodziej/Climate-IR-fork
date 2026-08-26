"""Midea remote families."""

from __future__ import annotations

from .profiles import MideaProfile

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (MideaProfile,)

__all__ = ["PROFILES", "MideaProfile"]
