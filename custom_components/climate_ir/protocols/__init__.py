"""Registry of the supported remote families, grouped by vendor.

To add a family, drop a module in the vendor package (or create a new vendor
package next to them) and list its profile in that package's `PROFILES`. The
platforms, the config flow, and the device controls pick it up from there.
Imports are explicit rather than discovered from disk, so nothing scans the
filesystem while Home Assistant is starting up.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import (
    daikin,
    fujitsu,
    hitachi,
    midea,
    mitsubishi_electric,
    mitsubishi_heavy,
    panasonic,
    toshiba,
)
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

#: Vendor packages, in the order their families are offered.
VENDORS: tuple = (
    mitsubishi_heavy,
    mitsubishi_electric,
    daikin,
    panasonic,
    midea,
    toshiba,
    fujitsu,
    hitachi,
)

_PROFILES: dict = {
    profile.key: profile
    for profile in (
        cls() for vendor in VENDORS for cls in vendor.PROFILES
    )
}

#: The family used by config entries created before families existed.
DEFAULT_PROTOCOL: str = mitsubishi_heavy.ZSAProfile.key


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
    "VENDORS",
    "all_profiles",
    "get_profile",
    "hvac_mode_to_protocol_mode",
    "protocol_keys",
]
