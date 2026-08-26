"""Hitachi remote families."""

from __future__ import annotations

from .profiles import HitachiProfile

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (HitachiProfile,)

__all__ = ["PROFILES", "HitachiProfile"]
