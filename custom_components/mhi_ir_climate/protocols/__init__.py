"""Registry of the supported remote families.

To add a family, drop a module next to this one that defines a
`ClimateProfile` subclass, and add it to `_PROFILE_CLASSES` below. The
platforms, the config flow, and the device controls pick it up from there.
Imports are explicit rather than discovered from disk, so nothing scans the
filesystem while Home Assistant is starting up.
"""

from __future__ import annotations

from collections.abc import Sequence

from .base import (
    ButtonControl,
    ClimateProfile,
    ClimateState,
    ConfigField,
    Control,
    EntityState,
    SelectControl,
    SwitchControl,
    hvac_mode_to_protocol_mode,
)
from .fd import FDProfile
from .zsa import ZSAProfile

_PROFILE_CLASSES: tuple = (
    ZSAProfile,
    FDProfile,
)

_PROFILES: dict = {profile.key: profile for profile in map(lambda cls: cls(), _PROFILE_CLASSES)}

#: The family used by config entries created before families existed.
DEFAULT_PROTOCOL: str = ZSAProfile.key


def all_profiles() -> Sequence[ClimateProfile]:
    """Return every registered profile, in registration order."""

    return tuple(_PROFILES.values())


def protocol_keys() -> Sequence[str]:
    """Return every registered profile key, in registration order."""

    return tuple(_PROFILES)


def get_profile(protocol: str | None) -> ClimateProfile:
    """Return the profile for a key, falling back to the default family."""

    return _PROFILES.get(protocol or DEFAULT_PROTOCOL, _PROFILES[DEFAULT_PROTOCOL])


__all__ = [
    "ButtonControl",
    "ClimateProfile",
    "ClimateState",
    "ConfigField",
    "Control",
    "DEFAULT_PROTOCOL",
    "EntityState",
    "SelectControl",
    "SwitchControl",
    "all_profiles",
    "get_profile",
    "hvac_mode_to_protocol_mode",
    "protocol_keys",
]
