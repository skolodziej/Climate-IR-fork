"""Fujitsu profiles. Unverified against hardware."""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import fujitsu_frames


class FujitsuProfile(ClimateProfile):
    """The generic Fujitsu frame.

    Switching off sends a short message of its own rather than a flag in the
    normal frame, so the state the entity holds is not transmitted then.
    """

    key = "fujitsu"
    name = "Fujitsu split"
    device_model = "Fujitsu (generic)"
    manufacturer = "Fujitsu"

    fan_modes = tuple(fujitsu_frames.FAN_CODES)
    default_fan_mode = fujitsu_frames.FAN_AUTO
    swing_modes = tuple(fujitsu_frames.SWING_CODES)
    default_swing_mode = fujitsu_frames.SWING_OFF
    swing_horizontal_modes = tuple(fujitsu_frames.SWING_H_CODES)
    default_swing_horizontal_mode = fujitsu_frames.SWING_OFF
    preset_modes = fujitsu_frames.PRESET_MODES
    min_temperature = fujitsu_frames.MIN_TEMPERATURE
    max_temperature = fujitsu_frames.MAX_TEMPERATURE

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        normalized = str(preset_mode).strip().lower()
        for preset in fujitsu_frames.PRESET_MODES:
            if normalized == preset.lower():
                return preset

        raise ValueError(f"Unknown preset mode: {preset_mode}")

    def build_command(self, state: ClimateState) -> Any:
        """Build a Fujitsu command."""

        return fujitsu_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
            swing_horizontal_mode=(
                state.swing_horizontal_mode or self.default_swing_horizontal_mode
            ),
            preset_mode=state.preset_mode,
        )
