"""Midea profiles. Unverified against hardware."""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import midea_frames


class MideaProfile(ClimateProfile):
    """The generic Midea frame, also sold under many other brands."""

    key = "midea"
    name = "Midea split"
    device_model = "Midea (generic)"
    manufacturer = "Midea"

    fan_modes = tuple(midea_frames.FAN_CODES)
    default_fan_mode = midea_frames.FAN_AUTO
    preset_modes = ("none",)
    min_temperature = midea_frames.MIN_TEMPERATURE
    max_temperature = midea_frames.MAX_TEMPERATURE

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        if str(preset_mode).strip().lower() != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"

    def build_command(self, state: ClimateState) -> Any:
        """Build a Midea command."""

        return midea_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
        )
