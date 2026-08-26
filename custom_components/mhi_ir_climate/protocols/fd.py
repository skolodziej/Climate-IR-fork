"""FD-series cassettes: 160-bit frames at 36 kHz, PJZ502A030D remote."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from homeassistant.components.climate.const import HVACMode

from .. import fd_protocol
from .base import (
    ButtonControl,
    ClimateProfile,
    ClimateState,
    Control,
    EntityState,
    hvac_mode_to_protocol_mode,
)

# High Power is verified in cool and heat and is rejected by the remote in fan
# only. Auto is unverified but harmless; dry is left out with it.
_POWER_PRESET_HVAC_MODES: Final = (
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.HEAT_COOL,
)


class FDProfile(ClimateProfile):
    """FDTC cassettes driven by the PJZ502A030D remote."""

    key = "fd"
    name = "FD series cassette"
    device_model = "MHI FD Series (PJZ502A030D)"

    fan_modes = fd_protocol.FAN_MODES
    default_fan_mode = fd_protocol.DEFAULT_FAN_MODE
    preset_modes = fd_protocol.PRESET_MODES
    swing_modes = fd_protocol.SWING_MODES
    default_swing_mode = fd_protocol.DEFAULT_SWING_MODE
    min_temperature = fd_protocol.MIN_TEMPERATURE
    max_temperature = fd_protocol.MAX_TEMPERATURE
    temperature_locking_presets = (
        fd_protocol.PRESET_BOOST,
        fd_protocol.PRESET_ECO,
    )

    # --- device controls ------------------------------------------------
    def controls(self) -> Sequence[Control]:
        """Return the FD device-page controls."""

        return (
            ButtonControl(
                key="filter_reset",
                name="Reset filter sign",
                extra="filter_reset",
            ),
        )

    # --- behaviour ------------------------------------------------------
    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        return fd_protocol.normalize_preset_mode(preset_mode)

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        if preset_mode == fd_protocol.PRESET_NONE:
            return True
        if hvac_mode == HVACMode.OFF:
            return False
        if preset_mode in (fd_protocol.PRESET_BOOST, fd_protocol.PRESET_ECO):
            return hvac_mode in _POWER_PRESET_HVAC_MODES

        return True

    def preset_temperature(
        self,
        preset_mode: str,
        hvac_mode: HVACMode,
    ) -> int | None:
        """Return the setpoint Eco writes for an HVAC mode.

        High Power writes an extreme value too, but that is a request for
        maximum output rather than a setpoint: the remote restores the
        previous temperature when High Power ends. The frame builder applies
        it on its own, so Home Assistant keeps showing the user's setpoint.
        """

        if preset_mode != fd_protocol.PRESET_ECO:
            return None

        return fd_protocol.forced_temperature(
            hvac_mode_to_protocol_mode(hvac_mode),
            eco=True,
        )

    def adjust_state(self, state: EntityState) -> None:
        """Remember the louver position the swing flag is combined with."""

        if state.swing_mode and state.swing_mode != fd_protocol.DEFAULT_SWING_MODE:
            state.last_swing_mode = state.swing_mode

    # --- encoding -------------------------------------------------------
    def build_command(self, state: ClimateState) -> Any:
        """Build an FD IR command.

        The unit treats Silent, Night Setback, High Power and Eco as
        independent bits, but a Home Assistant preset is single-select, so
        exactly one of them is ever set here.
        """

        preset_mode = fd_protocol.normalize_preset_mode(state.preset_mode)

        return fd_protocol.build_fd_ir_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or fd_protocol.DEFAULT_SWING_MODE,
            louver_position=_louver_position(state.last_swing_mode),
            silent=preset_mode == fd_protocol.PRESET_SILENT,
            night_setback=preset_mode == fd_protocol.PRESET_NIGHT_SETBACK,
            high_power=preset_mode == fd_protocol.PRESET_BOOST,
            eco=preset_mode == fd_protocol.PRESET_ECO,
            filter_reset=bool(state.extras.get("filter_reset", False)),
        )


def _louver_position(last_swing_mode: str | None) -> str:
    """Return a fixed louver position, never the swing toggle itself.

    `last_swing_mode` is whatever the entity last held, so it may legitimately
    be the swing value rather than a position.
    """

    if not last_swing_mode or last_swing_mode == fd_protocol.DEFAULT_SWING_MODE:
        return fd_protocol.DEFAULT_LOUVER_POSITION

    return last_swing_mode
