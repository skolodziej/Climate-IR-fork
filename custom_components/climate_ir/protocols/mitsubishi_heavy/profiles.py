"""Mitsubishi Heavy profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from homeassistant.components.climate.const import HVACMode

from . import fdtc_frames, zj_frames, zm_frames as ir_protocol
from ...const import CONF_BASE_FRAME_HEX
from ..base import (
    ButtonControl,
    ClimateProfile,
    ClimateState,
    ConfigField,
    Control,
    EntityState,
    SelectControl,
    SwitchControl,
    VERIFICATION_CAPTURES,
    VERIFICATION_HARDWARE,
    hvac_mode_to_protocol_mode,
)

SWING_3D_AUTO: Final = "3D Auto"
SWING_STOP: Final = "Stop"

_MODES_WITHOUT_3D_AUTO: Final = (HVACMode.DRY, HVACMode.FAN_ONLY)
_PRESETS_WITHOUT_3D_AUTO: Final = (
    ir_protocol.PRESET_BOOST,
    ir_protocol.PRESET_ECO,
)
_ECO_HVAC_MODES: Final = (
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.HEAT_COOL,
    HVACMode.DRY,
)
_PRESET_HVAC_MODES: Final = (HVACMode.COOL, HVACMode.HEAT, HVACMode.HEAT_COOL)
_AUTO_CLEAN_HVAC_MODES: Final = (HVACMode.COOL, HVACMode.DRY, HVACMode.HEAT_COOL)

BOOST_RESET_SECONDS: Final = 15 * 60


class ZSAProfile(ClimateProfile):
    """SRK/DXK ZSA units driven by the RLA502A remotes."""

    key = "zsa"
    name = "ZSA / Avanti wall-mounted"
    device_model = "ZSA Series (Avanti)"
    verification = VERIFICATION_HARDWARE

    fan_modes = ir_protocol.FAN_MODES
    default_fan_mode = ir_protocol.DEFAULT_FAN_MODE
    preset_modes = ir_protocol.PRESET_MODES
    swing_modes = ir_protocol.SWING_MODES
    swing_horizontal_modes = ir_protocol.SWING_HORIZONTAL_MODES
    default_swing_mode = SWING_3D_AUTO
    default_swing_horizontal_mode = SWING_3D_AUTO
    boost_reset_seconds = BOOST_RESET_SECONDS

    # --- config flow ----------------------------------------------------
    def config_fields(self) -> Sequence[ConfigField]:
        """The ZSA frame is built by patching a captured base frame."""

        return (
            ConfigField(
                key=CONF_BASE_FRAME_HEX,
                default=ir_protocol.DEFAULT_BASE_FRAME_HEX,
            ),
        )

    def validate_config(self, user_input: Mapping) -> Mapping:
        """Reject a base frame that is not 19 bytes of hexadecimal."""

        try:
            ir_protocol.validate_base_frame_hex(user_input[CONF_BASE_FRAME_HEX])
        except (ValueError, KeyError):
            return {CONF_BASE_FRAME_HEX: "invalid_base_frame"}
        return {}

    # --- device controls ------------------------------------------------
    def controls(self) -> Sequence[Control]:
        """Return the ZSA device-page controls."""

        return (
            SelectControl(
                key="led_brightness",
                name="Power LED brightness",
                options=ir_protocol.LED_BRIGHTNESS_MODES,
                default=ir_protocol.DEFAULT_LED_BRIGHTNESS,
            ),
            SelectControl(
                key="install_position",
                name="Installation position",
                options=ir_protocol.INSTALL_POSITION_MODES,
                default=ir_protocol.DEFAULT_INSTALL_POSITION,
                one_shot=True,
                requires_power_off=True,
            ),
            SwitchControl(
                key="auto_clean",
                name="Auto clean",
                default=ir_protocol.DEFAULT_AUTO_CLEAN,
            ),
        )

    def should_send_after_control_change(
        self,
        key: str,
        value: Any,
        hvac_mode: HVACMode,
    ) -> bool:
        """Auto clean still needs a command when it is switched off."""

        if key == "auto_clean":
            return hvac_mode != HVACMode.OFF or not value

        return hvac_mode != HVACMode.OFF

    def power_off_extras(
        self,
        previous_hvac_mode: HVACMode,
        options: Mapping,
    ) -> Mapping:
        """Powering off starts a clean cycle when auto clean is enabled."""

        if previous_hvac_mode in _AUTO_CLEAN_HVAC_MODES and options.get("auto_clean"):
            return {"start_auto_clean": True}

        return {}

    # --- behaviour ------------------------------------------------------
    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        return ir_protocol.normalize_preset_mode(preset_mode)

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        if preset_mode == ir_protocol.PRESET_NONE:
            return True
        if preset_mode == ir_protocol.PRESET_ECO:
            return hvac_mode in _ECO_HVAC_MODES
        if preset_mode == ir_protocol.PRESET_NIGHT_SETBACK:
            return hvac_mode == HVACMode.HEAT
        return hvac_mode in _PRESET_HVAC_MODES

    def hvac_mode_for_preset(
        self,
        preset_mode: str,
        hvac_mode: HVACMode,
    ) -> HVACMode | None:
        """Night Setback is a heat-mode function on this family."""

        if preset_mode == ir_protocol.PRESET_NIGHT_SETBACK:
            return HVACMode.HEAT

        return None

    def swing_mode_error(self, swing_mode: str, state: EntityState) -> str | None:
        """3D Auto cannot be combined with Boost or Eco."""

        return self._three_d_error(swing_mode, state)

    def swing_horizontal_mode_error(
        self,
        swing_horizontal_mode: str,
        state: EntityState,
    ) -> str | None:
        """3D Auto cannot be combined with Boost or Eco."""

        return self._three_d_error(swing_horizontal_mode, state)

    def _three_d_error(self, value: str, state: EntityState) -> str | None:
        if value == SWING_3D_AUTO and state.preset_mode in _PRESETS_WITHOUT_3D_AUTO:
            return (
                f"3D Auto is not available while preset mode "
                f"{state.preset_mode} is active"
            )
        return None

    def adjust_state(self, state: EntityState) -> None:
        """Keep the two swing axes coupled and honour the 3D Auto rules."""

        if state.hvac_mode == HVACMode.DRY:
            state.fan_mode = self.default_fan_mode

        blocked = (
            state.hvac_mode in _MODES_WITHOUT_3D_AUTO
            or state.preset_mode in _PRESETS_WITHOUT_3D_AUTO
        )

        if state.swing_horizontal_mode is None:
            state.swing_horizontal_mode = (
                SWING_3D_AUTO
                if state.swing_mode == SWING_3D_AUTO and not blocked
                else state.last_swing_horizontal_mode or SWING_STOP
            )

        if blocked:
            self._exit_3d_auto(state)
        elif state.changed == "swing_mode":
            self._couple_from_vertical(state)
        elif state.changed == "swing_horizontal_mode":
            self._couple_from_horizontal(state)
        elif SWING_3D_AUTO in (state.swing_mode, state.swing_horizontal_mode):
            state.swing_mode = SWING_3D_AUTO
            state.swing_horizontal_mode = SWING_3D_AUTO

        self._remember_positions(state)

    def _couple_from_vertical(self, state: EntityState) -> None:
        if state.swing_mode == SWING_3D_AUTO:
            state.swing_horizontal_mode = SWING_3D_AUTO
        elif state.swing_horizontal_mode == SWING_3D_AUTO:
            state.swing_horizontal_mode = (
                state.last_swing_horizontal_mode or SWING_STOP
            )

    def _couple_from_horizontal(self, state: EntityState) -> None:
        if state.swing_horizontal_mode == SWING_3D_AUTO:
            state.swing_mode = SWING_3D_AUTO
        elif state.swing_mode == SWING_3D_AUTO:
            state.swing_mode = state.last_swing_mode or SWING_STOP

    def _exit_3d_auto(self, state: EntityState) -> None:
        if state.swing_mode == SWING_3D_AUTO:
            state.swing_mode = state.last_swing_mode or SWING_STOP
        if state.swing_horizontal_mode == SWING_3D_AUTO:
            state.swing_horizontal_mode = (
                state.last_swing_horizontal_mode or SWING_STOP
            )

    def _remember_positions(self, state: EntityState) -> None:
        if state.swing_mode != SWING_3D_AUTO:
            state.last_swing_mode = state.swing_mode
        if state.swing_horizontal_mode != SWING_3D_AUTO:
            state.last_swing_horizontal_mode = state.swing_horizontal_mode

    # --- encoding -------------------------------------------------------
    def build_command(self, state: ClimateState) -> Any:
        """Build a ZSA IR command."""

        return ir_protocol.build_zm_command(
            state.mode,
            state.temperature,
            state.power_on,
            base_frame_hex=state.config.get(CONF_BASE_FRAME_HEX, ""),
            auto_clean=bool(state.options.get("auto_clean", False)),
            fan_mode=state.fan_mode,
            led_brightness=state.options.get(
                "led_brightness", ir_protocol.DEFAULT_LED_BRIGHTNESS
            ),
            preset_mode=state.preset_mode,
            start_auto_clean=bool(state.extras.get("start_auto_clean", False)),
            install_position=state.extras.get("install_position"),
            swing_ud=state.swing_mode,
            swing_lr=state.swing_horizontal_mode,
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
    device_model = "FD Series (PJZ502A030D)"
    verification = VERIFICATION_HARDWARE

    fan_modes = fdtc_frames.FAN_MODES
    default_fan_mode = fdtc_frames.DEFAULT_FAN_MODE
    preset_modes = fdtc_frames.PRESET_MODES
    swing_modes = fdtc_frames.SWING_MODES
    default_swing_mode = fdtc_frames.DEFAULT_SWING_MODE
    min_temperature = fdtc_frames.MIN_TEMPERATURE
    max_temperature = fdtc_frames.MAX_TEMPERATURE
    temperature_locking_presets = (
        fdtc_frames.PRESET_BOOST,
        fdtc_frames.PRESET_ECO,
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

        return fdtc_frames.normalize_preset_mode(preset_mode)

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        if preset_mode == fdtc_frames.PRESET_NONE:
            return True
        if hvac_mode == HVACMode.OFF:
            return False
        if preset_mode in (fdtc_frames.PRESET_BOOST, fdtc_frames.PRESET_ECO):
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

        if preset_mode != fdtc_frames.PRESET_ECO:
            return None

        return fdtc_frames.forced_temperature(
            hvac_mode_to_protocol_mode(hvac_mode),
            eco=True,
        )

    def adjust_state(self, state: EntityState) -> None:
        """Remember the louver position the swing flag is combined with."""

        if state.swing_mode and state.swing_mode != fdtc_frames.DEFAULT_SWING_MODE:
            state.last_swing_mode = state.swing_mode

    # --- encoding -------------------------------------------------------
    def build_command(self, state: ClimateState) -> Any:
        """Build an FD IR command.

        The unit treats Silent, Night Setback, High Power and Eco as
        independent bits, but a Home Assistant preset is single-select, so
        exactly one of them is ever set here.
        """

        preset_mode = fdtc_frames.normalize_preset_mode(state.preset_mode)

        return fdtc_frames.build_fd_ir_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or fdtc_frames.DEFAULT_SWING_MODE,
            louver_position=_louver_position(state.last_swing_mode),
            silent=preset_mode == fdtc_frames.PRESET_SILENT,
            night_setback=preset_mode == fdtc_frames.PRESET_NIGHT_SETBACK,
            high_power=preset_mode == fdtc_frames.PRESET_BOOST,
            eco=preset_mode == fdtc_frames.PRESET_ECO,
            filter_reset=bool(state.extras.get("filter_reset", False)),
        )


def _louver_position(last_swing_mode: str | None) -> str:
    """Return a fixed louver position, never the swing toggle itself.

    `last_swing_mode` is whatever the entity last held, so it may legitimately
    be the swing value rather than a position.
    """

    if not last_swing_mode or last_swing_mode == fdtc_frames.DEFAULT_SWING_MODE:
        return fdtc_frames.DEFAULT_LOUVER_POSITION

    return last_swing_mode


class _ZJFamilyProfile(ClimateProfile):
    """Shared behaviour for the 11-byte SRK variants (ZJ, ZMP, ZEA).

    Unverified against hardware: built from the reference description only.
    """

    variant: Any = None

    min_temperature = zj_frames.MIN_TEMPERATURE
    max_temperature = zj_frames.MAX_TEMPERATURE
    preset_modes = ("none",)

    @property
    def fan_modes(self) -> tuple:
        """Return the fan speeds this variant encodes."""

        return tuple(self.variant.fan_codes)

    @property
    def default_fan_mode(self) -> str:
        """Auto is the first entry in every variant's table."""

        return zj_frames.FAN_AUTO

    @property
    def swing_modes(self) -> tuple:
        """Return the vertical positions this variant encodes."""

        return tuple(self.variant.swing_codes)

    @property
    def swing_horizontal_modes(self) -> tuple:
        """Return the horizontal positions this variant encodes."""

        return tuple(self.variant.swing_h_codes)

    @property
    def default_swing_mode(self) -> str:
        """Default to the stopped louver."""

        return zj_frames.SWING_STOP

    @property
    def default_swing_horizontal_mode(self) -> str:
        """Default to the stopped louver."""

        return zj_frames.SWING_H_STOP

    def controls(self) -> Sequence[Control]:
        """These variants carry a clean-cycle flag in every frame."""

        return (SwitchControl(key="clean", name="Clean", default=False),)

    def normalize_preset_mode(self, preset_mode: str) -> str:
        """This family has no presets beyond none."""

        normalized = str(preset_mode).strip().lower()
        if normalized != "none":
            raise ValueError(f"Unknown preset mode: {preset_mode}")

        return "none"

    def adjust_state(self, state: EntityState) -> None:
        """Dry runs with the auto fan speed only.

        Every captured dry frame carries the auto fan speed regardless of what
        was asked for, so the remote clearly forces it.
        """

        if state.hvac_mode == HVACMode.DRY:
            state.fan_mode = zj_frames.FAN_AUTO

    def build_command(self, state: ClimateState) -> Any:
        """Build an 11-byte Mitsubishi Heavy command."""

        return zj_frames.build_command(
            self.variant,
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
            swing_mode=state.swing_mode or self.default_swing_mode,
            swing_horizontal_mode=(
                state.swing_horizontal_mode or self.default_swing_horizontal_mode
            ),
            clean=bool(state.options.get("clean", False)),
        )


class ZJProfile(_ZJFamilyProfile):
    """SRKxxZJ-S units, remote RKX502A001C."""

    key = "mhi_zj"
    name = "SRK ZJ-S wall-mounted"
    device_model = "SRK ZJ-S Series"
    verification = VERIFICATION_CAPTURES
    variant = zj_frames.ZJ


class ZMPProfile(_ZJFamilyProfile):
    """SRK ZMP variant, which uses its own fan-only code."""

    key = "mhi_zmp"
    name = "SRK ZMP wall-mounted"
    device_model = "SRK ZMP Series"
    variant = zj_frames.ZMP


class ZEAProfile(_ZJFamilyProfile):
    """SRK ZEA variant, with four fan speeds and wider air direction codes."""

    key = "mhi_zea"
    name = "SRK ZEA wall-mounted"
    device_model = "SRK ZEA Series"
    variant = zj_frames.ZEA
