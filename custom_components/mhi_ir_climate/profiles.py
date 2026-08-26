"""Protocol profiles for the supported MHI remote families.

Each profile pairs the capabilities a Home Assistant entity should expose with
the frame builder that encodes them, so the platforms stay free of
protocol-specific branching.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from homeassistant.components.climate.const import HVACMode

from . import fd_protocol, ir_protocol
from .const import DEFAULT_PROTOCOL, PROTOCOL_FD, PROTOCOL_ZSA

BOOST_RESET_SECONDS: Final = 15 * 60


@dataclass
class CommandRequest:
    """The full state one IR frame has to describe."""

    mode: str
    temperature: int
    power_on: bool
    fan_mode: str
    preset_mode: str
    base_frame_hex: str = ""
    swing_mode: str | None = None
    swing_horizontal_mode: str | None = None
    louver_position: str | None = None
    led_brightness: str | None = None
    install_position: str | None = None
    auto_clean: bool = False
    start_auto_clean: bool = False
    filter_reset: bool = False


class ClimateProfile:
    """Capabilities and frame building for one MHI remote family."""

    key: str = ""
    device_model: str = ""
    fan_modes: tuple = ()
    default_fan_mode: str = ""
    preset_modes: tuple = ()
    swing_modes: tuple = ()
    swing_horizontal_modes: tuple = ()
    default_swing_mode: str = ""
    default_swing_horizontal_mode: str | None = None
    min_temperature: int = 18
    max_temperature: int = 30
    default_temperature: int = 24
    requires_base_frame: bool = False
    supports_3d_auto: bool = False
    supports_auto_clean: bool = False
    supports_led_brightness: bool = False
    supports_install_position: bool = False
    supports_filter_reset: bool = False
    dry_forces_auto_fan: bool = False
    night_setback_forces_heat: bool = False
    boost_reset_seconds: int | None = None
    temperature_locking_presets: tuple = ()

    @property
    def supports_horizontal_swing(self) -> bool:
        """Return whether the family has a separate horizontal swing axis."""

        return bool(self.swing_horizontal_modes)

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        raise NotImplementedError

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        raise NotImplementedError

    def preset_temperature(
        self,
        preset_mode: str,
        hvac_mode: HVACMode,
    ) -> int | None:
        """Return the setpoint a preset forces, or None when it is free."""

        return None

    def build_command(self, request: CommandRequest) -> Any:
        """Build the IR command for a requested state."""

        raise NotImplementedError

    def validate_base_frame(self, base_frame_hex: str) -> None:
        """Validate a configured base frame."""

        return None


class ZSAProfile(ClimateProfile):
    """ZSA/Avanti wall-mounted units, 19-byte frames at 38 kHz."""

    key = PROTOCOL_ZSA
    device_model = "MHI ZSA Series (Avanti)"
    fan_modes = ir_protocol.FAN_MODES
    default_fan_mode = ir_protocol.DEFAULT_FAN_MODE
    preset_modes = ir_protocol.PRESET_MODES
    swing_modes = ir_protocol.SWING_MODES
    swing_horizontal_modes = ir_protocol.SWING_HORIZONTAL_MODES
    default_swing_mode = "3D Auto"
    default_swing_horizontal_mode = "3D Auto"
    requires_base_frame = True
    supports_3d_auto = True
    supports_auto_clean = True
    supports_led_brightness = True
    supports_install_position = True
    dry_forces_auto_fan = True
    night_setback_forces_heat = True
    boost_reset_seconds = BOOST_RESET_SECONDS

    _ECO_HVAC_MODES: Final = (
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.HEAT_COOL,
        HVACMode.DRY,
    )
    _PRESET_HVAC_MODES: Final = (
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.HEAT_COOL,
    )

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        return ir_protocol.normalize_preset_mode(preset_mode)

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        if preset_mode == ir_protocol.PRESET_NONE:
            return True
        if preset_mode == ir_protocol.PRESET_ECO:
            return hvac_mode in self._ECO_HVAC_MODES
        if preset_mode == ir_protocol.PRESET_NIGHT_SETBACK:
            return hvac_mode == HVACMode.HEAT
        return hvac_mode in self._PRESET_HVAC_MODES

    def build_command(self, request: CommandRequest) -> Any:
        """Build a ZSA IR command."""

        return ir_protocol.build_mhi_ir_command(
            request.mode,
            request.temperature,
            request.power_on,
            base_frame_hex=request.base_frame_hex,
            auto_clean=request.auto_clean,
            fan_mode=request.fan_mode,
            led_brightness=request.led_brightness
            or ir_protocol.DEFAULT_LED_BRIGHTNESS,
            preset_mode=request.preset_mode,
            start_auto_clean=request.start_auto_clean,
            install_position=request.install_position,
            swing_ud=request.swing_mode,
            swing_lr=request.swing_horizontal_mode,
        )

    def validate_base_frame(self, base_frame_hex: str) -> None:
        """Validate the 19-byte ZSA base frame."""

        ir_protocol.validate_base_frame_hex(base_frame_hex)


class FDProfile(ClimateProfile):
    """FD-series cassettes driven by PJZ502A030D, 160-bit frames at 36 kHz."""

    key = PROTOCOL_FD
    device_model = "MHI FD Series (PJZ502A030D)"
    fan_modes = fd_protocol.FAN_MODES
    default_fan_mode = fd_protocol.DEFAULT_FAN_MODE
    preset_modes = fd_protocol.PRESET_MODES
    swing_modes = fd_protocol.SWING_MODES
    default_swing_mode = fd_protocol.DEFAULT_SWING_MODE
    min_temperature = fd_protocol.MIN_TEMPERATURE
    max_temperature = fd_protocol.MAX_TEMPERATURE
    supports_filter_reset = True
    temperature_locking_presets = (
        fd_protocol.PRESET_BOOST,
        fd_protocol.PRESET_ECO,
    )

    # High Power is verified in cool and heat and is rejected by the remote in
    # fan only. Auto is unverified but harmless; dry is left out with it.
    _POWER_PRESET_HVAC_MODES: Final = (
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.HEAT_COOL,
    )

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
            return hvac_mode in self._POWER_PRESET_HVAC_MODES
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

    def build_command(self, request: CommandRequest) -> Any:
        """Build an FD IR command.

        The unit treats Silent, Night Setback, High Power and Eco as
        independent bits, but a Home Assistant preset is single-select, so
        exactly one of them is ever set here.
        """

        preset_mode = fd_protocol.normalize_preset_mode(request.preset_mode)

        return fd_protocol.build_fd_ir_command(
            request.mode,
            request.temperature,
            request.power_on,
            fan_mode=request.fan_mode,
            swing_mode=request.swing_mode or fd_protocol.DEFAULT_SWING_MODE,
            louver_position=request.louver_position
            or fd_protocol.DEFAULT_LOUVER_POSITION,
            silent=preset_mode == fd_protocol.PRESET_SILENT,
            night_setback=preset_mode == fd_protocol.PRESET_NIGHT_SETBACK,
            high_power=preset_mode == fd_protocol.PRESET_BOOST,
            eco=preset_mode == fd_protocol.PRESET_ECO,
            filter_reset=request.filter_reset,
        )


PROFILES: Final = {
    PROTOCOL_ZSA: ZSAProfile(),
    PROTOCOL_FD: FDProfile(),
}


def get_profile(protocol: str | None) -> ClimateProfile:
    """Return the profile for a configured protocol key."""

    return PROFILES.get(protocol or DEFAULT_PROTOCOL, PROFILES[DEFAULT_PROTOCOL])


def hvac_mode_to_protocol_mode(hvac_mode: HVACMode) -> str:
    """Map a Home Assistant HVAC mode to the shared protocol mode names."""

    if hvac_mode == HVACMode.HEAT:
        return "heat"
    if hvac_mode == HVACMode.DRY:
        return "dry"
    if hvac_mode == HVACMode.FAN_ONLY:
        return "fan_only"
    if hvac_mode == HVACMode.HEAT_COOL:
        return "heat_cool"
    return "cool"
