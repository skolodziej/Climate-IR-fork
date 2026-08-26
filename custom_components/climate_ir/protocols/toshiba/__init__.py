"""Toshiba remote families."""

from __future__ import annotations

from .profiles import ToshibaProfile

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (ToshibaProfile,)

__all__ = ["PROFILES", "ToshibaProfile"]
