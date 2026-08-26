"""Fujitsu remote families."""

from __future__ import annotations

from .profiles import FujitsuProfile

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (FujitsuProfile,)

__all__ = ["PROFILES", "FujitsuProfile"]
