"""Panasonic remote families."""

from __future__ import annotations

from .profiles import (
    PanasonicDKEProfile,
    PanasonicEKEProfile,
    PanasonicJKEProfile,
    PanasonicLKEProfile,
    PanasonicNKEProfile,
)

#: Every profile this vendor contributes, in the order they are offered.
PROFILES: tuple = (
    PanasonicDKEProfile,
    PanasonicJKEProfile,
    PanasonicNKEProfile,
    PanasonicLKEProfile,
    PanasonicEKEProfile,
)

__all__ = ["PROFILES"] + [cls.__name__ for cls in PROFILES]
