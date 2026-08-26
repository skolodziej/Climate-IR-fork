"""Panasonic profiles.

Five remote generations share one frame format, so they share one builder and
differ only in the variant they hand it. All are **unverified against
hardware**.
"""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import panasonic_frames


class _PanasonicProfile(ClimateProfile):
    """Shared behaviour for the 27-byte Panasonic frame."""

    manufacturer = "Panasonic"
    variant: Any = None

    fan_modes = tuple(panasonic_frames.FAN_CODES)
    default_fan_mode = panasonic_frames.FAN_AUTO
    swing_modes = tuple(panasonic_frames.SWING_CODES)
    default_swing_mode = panasonic_frames.SWING_AUTO
    preset_modes = panasonic_frames.PRESET_MODES
    min_temperature = panasonic_frames.MIN_TEMPERATURE
    max_temperature = panasonic_frames.MAX_TEMPERATURE

    @property
    def swing_horizontal_modes(self) -> tuple:
        """Only the DKE remote can aim the horizontal louver."""

        if not self.variant.horizontal_swing:
            return ()

        return tuple(panasonic_frames.SWING_H_CODES)

    @property
    def default_swing_horizontal_mode(self) -> str | None:
        """Return the default horizontal position, if the model has one."""

        if not self.variant.horizontal_swing:
            return None

        return panasonic_frames.SWING_H_AUTO

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        for preset in panasonic_frames.PRESET_MODES:
            if str(preset_mode).strip().lower() == preset.lower():
                return preset

        raise ValueError(f"Unknown preset mode: {preset_mode}")

    def build_command(self, state: ClimateState) -> Any:
        """Build a 27-byte Panasonic command."""

        return panasonic_frames.build_command(
            self.variant,
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
            swing_horizontal_mode=(
                state.swing_horizontal_mode or panasonic_frames.SWING_H_AUTO
            ),
            preset_mode=state.preset_mode,
        )


class PanasonicDKEProfile(_PanasonicProfile):
    """DKE remotes, the only generation with horizontal louver control."""

    key = "panasonic_dke"
    name = "Panasonic DKE"
    device_model = "DKE"
    variant = panasonic_frames.DKE


class PanasonicJKEProfile(_PanasonicProfile):
    """JKE remotes."""

    key = "panasonic_jke"
    name = "Panasonic JKE"
    device_model = "JKE"
    variant = panasonic_frames.JKE


class PanasonicNKEProfile(_PanasonicProfile):
    """NKE remotes."""

    key = "panasonic_nke"
    name = "Panasonic NKE"
    device_model = "NKE"
    variant = panasonic_frames.NKE


class PanasonicLKEProfile(_PanasonicProfile):
    """LKE remotes."""

    key = "panasonic_lke"
    name = "Panasonic LKE"
    device_model = "LKE"
    variant = panasonic_frames.LKE


class PanasonicEKEProfile(_PanasonicProfile):
    """EKE remotes, which transmit the setpoint bit-reversed."""

    key = "panasonic_eke"
    name = "Panasonic EKE"
    device_model = "EKE"
    variant = panasonic_frames.EKE
