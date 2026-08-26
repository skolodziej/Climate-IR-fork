"""Daikin profiles. Unverified against hardware."""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import daikin_frames


class DaikinProfile(ClimateProfile):
    """The generic Daikin frame, as used across many split units.

    The reference this is built from drives the louvers from the unit's own
    settings rather than from the frame, so no swing axis is offered.
    """

    key = "daikin"
    name = "Daikin split"
    device_model = "Daikin (generic)"
    manufacturer = "Daikin"

    fan_modes = tuple(daikin_frames.FAN_CODES)
    default_fan_mode = daikin_frames.FAN_AUTO
    preset_modes = ("none",)
    min_temperature = daikin_frames.MIN_TEMPERATURE
    max_temperature = daikin_frames.MAX_TEMPERATURE

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        if str(preset_mode).strip().lower() != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"

    def build_command(self, state: ClimateState) -> Any:
        """Build a 35-byte Daikin command."""

        return daikin_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
        )
