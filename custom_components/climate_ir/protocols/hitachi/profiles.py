"""Hitachi profiles. Unverified against hardware."""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import hitachi_frames


class HitachiProfile(ClimateProfile):
    """The generic Hitachi frame.

    Both louvers are a plain on/off swing rather than a set of positions.
    """

    key = "hitachi"
    name = "Hitachi split"
    device_model = "Hitachi (generic)"
    manufacturer = "Hitachi"

    fan_modes = tuple(hitachi_frames.FAN_CODES)
    default_fan_mode = hitachi_frames.FAN_AUTO
    swing_modes = tuple(hitachi_frames.SWING_CODES)
    default_swing_mode = hitachi_frames.SWING_OFF
    swing_horizontal_modes = tuple(hitachi_frames.SWING_H_CODES)
    default_swing_horizontal_mode = hitachi_frames.SWING_OFF
    preset_modes = ("none",)
    min_temperature = hitachi_frames.MIN_TEMPERATURE
    max_temperature = hitachi_frames.MAX_TEMPERATURE

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        if str(preset_mode).strip().lower() != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"

    def build_command(self, state: ClimateState) -> Any:
        """Build a 28-byte Hitachi command."""

        return hitachi_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
            swing_horizontal_mode=(
                state.swing_horizontal_mode or self.default_swing_horizontal_mode
            ),
        )
