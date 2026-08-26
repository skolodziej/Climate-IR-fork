"""Mitsubishi Electric profiles.

All of these are built from the reference description only and are
**unverified against hardware**.
"""

from __future__ import annotations

from typing import Any

from ..base import ClimateProfile, ClimateState
from . import msc_frames, msz_frames, sez_frames


class _NoPresetProfile(ClimateProfile):
    """Shared plumbing for families without presets."""

    preset_modes = ("none",)

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        normalized = str(preset_mode).strip().lower()
        if normalized != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"


class _MSZProfile(_NoPresetProfile):
    """Shared behaviour for the 18-byte MSZ variants."""

    manufacturer = "Mitsubishi Electric"
    variant: Any = None

    fan_modes = tuple(msz_frames.FAN_CODES)
    default_fan_mode = msz_frames.FAN_AUTO
    swing_horizontal_modes = tuple(msz_frames.SWING_H_CODES)
    default_swing_horizontal_mode = msz_frames.SWING_H_AUTO
    min_temperature = msz_frames.MIN_TEMPERATURE
    max_temperature = msz_frames.MAX_TEMPERATURE

    @property
    def swing_modes(self) -> tuple:
        """Return the vertical positions this variant encodes."""

        return tuple(self.variant.swing_codes)

    @property
    def default_swing_mode(self) -> str:
        """Default to the automatic louver."""

        return msz_frames.SWING_AUTO

    def build_command(self, state: ClimateState) -> Any:
        """Build an 18-byte Mitsubishi Electric command."""

        return msz_frames.build_command(
            self.variant,
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
            swing_horizontal_mode=(
                state.swing_horizontal_mode or self.default_swing_horizontal_mode
            ),
        )


class MSZFDProfile(_MSZProfile):
    """MSZ-FD wall-mounted units."""

    key = "mel_msz_fd"
    name = "MSZ-FD wall-mounted"
    device_model = "Mitsubishi Electric MSZ-FD"
    variant = msz_frames.FD


class MSZFEProfile(_MSZProfile):
    """MSZ-FE wall-mounted units."""

    key = "mel_msz_fe"
    name = "MSZ-FE wall-mounted"
    device_model = "Mitsubishi Electric MSZ-FE"
    variant = msz_frames.FE


class MSYProfile(_MSZProfile):
    """MSY wall-mounted units."""

    key = "mel_msy"
    name = "MSY wall-mounted"
    device_model = "Mitsubishi Electric MSY"
    variant = msz_frames.MSY


class MSZFAProfile(_MSZProfile):
    """MSZ-FA units, which use their own mode and louver codes."""

    key = "mel_msz_fa"
    name = "MSZ-FA wall-mounted"
    device_model = "Mitsubishi Electric MSZ-FA"
    variant = msz_frames.FA


class MSZKJProfile(_MSZProfile):
    """MSZ-KJ units."""

    key = "mel_msz_kj"
    name = "MSZ-KJ wall-mounted"
    device_model = "Mitsubishi Electric MSZ-KJ"
    variant = msz_frames.KJ


class MSCProfile(_NoPresetProfile):
    """MSC units, a 14-byte frame with a summed checksum."""

    key = "mel_msc"
    name = "MSC wall-mounted"
    device_model = "Mitsubishi Electric MSC"
    manufacturer = "Mitsubishi Electric"

    fan_modes = tuple(msc_frames.FAN_CODES)
    default_fan_mode = msc_frames.FAN_AUTO
    swing_modes = tuple(msc_frames.SWING_CODES)
    default_swing_mode = msc_frames.SWING_AUTO
    min_temperature = msc_frames.MIN_TEMPERATURE
    max_temperature = msc_frames.MAX_TEMPERATURE

    def build_command(self, state: ClimateState) -> Any:
        """Build a 14-byte Mitsubishi Electric MSC command."""

        return msc_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
        )


class SEZKDXXProfile(_NoPresetProfile):
    """SEZ-KDXX ducted units. No louver control, three fan speeds."""

    key = "mel_sez_kdxx"
    name = "SEZ-KDXX ducted"
    device_model = "Mitsubishi Electric SEZ-KDXX"
    manufacturer = "Mitsubishi Electric"

    fan_modes = tuple(sez_frames.FAN_CODES)
    default_fan_mode = sez_frames.FAN_LOW
    min_temperature = sez_frames.MIN_TEMPERATURE
    max_temperature = sez_frames.MAX_TEMPERATURE

    def build_command(self, state: ClimateState) -> Any:
        """Build a 17-byte Mitsubishi Electric SEZ-KDXX command."""

        return sez_frames.build_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
        )
