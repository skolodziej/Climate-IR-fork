"""Toshiba profiles. Unverified against hardware."""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import toshiba_frames


class ToshibaProfile(ClimateProfile):
    """The generic Toshiba frame.

    Power off is a mode code rather than a flag, and the remote has no
    fan-only code of its own, so fan-only rides on the dry code.
    """

    key = "toshiba"
    name = "Toshiba split"
    device_model = "Toshiba (generic)"
    manufacturer = "Toshiba"

    fan_modes = tuple(toshiba_frames.FAN_CODES)
    default_fan_mode = toshiba_frames.FAN_AUTO
    preset_modes = ("none",)
    min_temperature = toshiba_frames.MIN_TEMPERATURE
    max_temperature = toshiba_frames.MAX_TEMPERATURE

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        if str(preset_mode).strip().lower() != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"

    def build_command(self, state: ClimateState) -> Any:
        """Build a nine-byte Toshiba command."""

        return toshiba_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
        )
