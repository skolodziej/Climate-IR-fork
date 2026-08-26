"""ZSA/Avanti wall-mounted units: 19-byte frames at 38 kHz."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from homeassistant.components.climate.const import HVACMode

from .. import ir_protocol
from ..const import CONF_BASE_FRAME_HEX
from .base import (
    ClimateProfile,
    ClimateState,
    ConfigField,
    Control,
    EntityState,
    SelectControl,
    SwitchControl,
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
    device_model = "MHI ZSA Series (Avanti)"

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

        return ir_protocol.build_mhi_ir_command(
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
