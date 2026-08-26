"""The contract a protocol profile implements.

One profile describes one remote family: what the Home Assistant entities may
offer, how that state becomes an IR frame, and which quirks the family has.
Everything a family does not share with the others is expressed here rather
than branched on in the platforms, so adding a family does not touch them.

See `docs/adding-a-protocol.md` for a walkthrough.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.climate.const import HVACMode

PRESET_NONE = "none"

DEFAULT_HVAC_MODES: tuple = (
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT_COOL,
)


@dataclass(frozen=True)
class ConfigField:
    """One extra field a profile needs in the config flow.

    Rendered by the config flow, so profiles stay free of voluptuous and of
    Home Assistant's selector types.
    """

    key: str
    selector: str = "text"
    required: bool = True
    default: Any = None


@dataclass(frozen=True)
class SelectControl:
    """A select entity on the device page."""

    key: str
    name: str
    options: tuple
    default: str
    # One-shot controls send their value with a single command instead of
    # being carried in every frame.
    one_shot: bool = False
    requires_power_off: bool = False


@dataclass(frozen=True)
class SwitchControl:
    """A switch entity on the device page."""

    key: str
    name: str
    default: bool = False


@dataclass(frozen=True)
class ButtonControl:
    """A button entity that sends one command."""

    key: str
    name: str
    # Passed to build_command in `extras` for that single command.
    extra: str | None = None
    requires_power_on: bool = False


Control = Any  # SelectControl | SwitchControl | ButtonControl


@dataclass
class EntityState:
    """The user-visible state, handed to a profile so it can reconcile it.

    A profile may mutate this in `adjust_state` to enforce family rules, for
    example coupling two swing axes or forcing a fan speed in a mode that has
    only one.
    """

    hvac_mode: HVACMode
    temperature: int
    fan_mode: str
    preset_mode: str
    swing_mode: str | None = None
    swing_horizontal_mode: str | None = None
    last_swing_mode: str | None = None
    last_swing_horizontal_mode: str | None = None
    #: Which attribute the user just changed, so a profile can react to the
    #: change rather than only to the resulting state. None while restoring.
    changed: str | None = None


@dataclass
class ClimateState:
    """Everything one IR frame has to describe."""

    mode: str
    temperature: int
    power_on: bool
    fan_mode: str
    preset_mode: str
    swing_mode: str | None = None
    swing_horizontal_mode: str | None = None
    # The last fixed positions, for families whose swing flag is separate from
    # the position it swings around.
    last_swing_mode: str | None = None
    last_swing_horizontal_mode: str | None = None
    # Values from the config entry, keyed by the profile's own ConfigFields.
    config: Mapping = field(default_factory=dict)
    # Persistent device controls, keyed by the profile's own Control keys.
    options: Mapping = field(default_factory=dict)
    # One-shot values that apply to this command only.
    extras: Mapping = field(default_factory=dict)


class ClimateProfile:
    """Capabilities, behaviour, and frame building for one remote family.

    Only `key`, `name`, `device_model`, the vocabularies, `normalize_preset_mode`
    and `build_command` have to be provided. Everything else has a default that
    suits a family without that feature.
    """

    # --- identity -------------------------------------------------------
    key: str = ""
    name: str = ""
    manufacturer: str = "Mitsubishi Heavy Industries"
    device_model: str = ""

    # --- what the entity may offer --------------------------------------
    hvac_modes: tuple = DEFAULT_HVAC_MODES
    fan_modes: tuple = ()
    default_fan_mode: str = ""
    preset_modes: tuple = (PRESET_NONE,)
    default_preset_mode: str = PRESET_NONE
    swing_modes: tuple = ()
    swing_horizontal_modes: tuple = ()
    default_swing_mode: str | None = None
    default_swing_horizontal_mode: str | None = None
    min_temperature: int = 18
    max_temperature: int = 30
    default_temperature: int = 24
    temperature_step: int = 1
    # Presets that own the setpoint, so a temperature change clears them.
    temperature_locking_presets: tuple = ()
    # Clear Boost in Home Assistant state after this long, for units that end
    # it on their own. None keeps it until something else changes it.
    boost_reset_seconds: int | None = None

    @property
    def supports_swing(self) -> bool:
        """Return whether the family has a vertical swing axis."""

        return bool(self.swing_modes)

    @property
    def supports_horizontal_swing(self) -> bool:
        """Return whether the family has a separate horizontal swing axis."""

        return bool(self.swing_horizontal_modes)

    # --- config flow ----------------------------------------------------
    def config_fields(self) -> Sequence[ConfigField]:
        """Return extra config entry fields this family needs."""

        return ()

    def validate_config(self, user_input: Mapping) -> Mapping:
        """Return {field key: error key} for invalid values."""

        return {}

    # --- device controls ------------------------------------------------
    def controls(self) -> Sequence[Control]:
        """Return the device-page controls this family offers."""

        return ()

    def should_send_after_control_change(
        self,
        key: str,
        value: Any,
        hvac_mode: HVACMode,
    ) -> bool:
        """Return whether changing a control should send a command now."""

        return hvac_mode != HVACMode.OFF

    def power_off_extras(
        self,
        previous_hvac_mode: HVACMode,
        options: Mapping,
    ) -> Mapping:
        """Return one-shot extras to add to the command that powers off."""

        return {}

    # --- behaviour ------------------------------------------------------
    def normalize_preset_mode(self, preset_mode: str) -> str:
        """Return the canonical name for a preset."""

        raise NotImplementedError

    def preset_available(self, preset_mode: str, hvac_mode: HVACMode) -> bool:
        """Return whether a preset may be active in an HVAC mode."""

        return preset_mode == PRESET_NONE or hvac_mode != HVACMode.OFF

    def preset_temperature(
        self,
        preset_mode: str,
        hvac_mode: HVACMode,
    ) -> int | None:
        """Return the setpoint a preset forces, or None when it is free."""

        return None

    def hvac_mode_for_preset(
        self,
        preset_mode: str,
        hvac_mode: HVACMode,
    ) -> HVACMode | None:
        """Return the HVAC mode a preset requires, or None if it is free."""

        return None

    def adjust_state(self, state: EntityState) -> None:
        """Reconcile user-visible state after a change, in place."""

        return None

    def swing_mode_error(
        self,
        swing_mode: str,
        state: EntityState,
    ) -> str | None:
        """Return why a vertical swing value cannot be set, or None."""

        return None

    def swing_horizontal_mode_error(
        self,
        swing_horizontal_mode: str,
        state: EntityState,
    ) -> str | None:
        """Return why a horizontal swing value cannot be set, or None."""

        return None

    # --- encoding -------------------------------------------------------
    def build_command(self, state: ClimateState) -> Any:
        """Build the IR command for a state."""

        raise NotImplementedError


def hvac_mode_to_protocol_mode(hvac_mode: HVACMode) -> str:
    """Map a Home Assistant HVAC mode to the shared protocol mode names.

    The families documented so far all use this vocabulary; a family that
    needs a different one can ignore it and read `ClimateState.mode` itself.
    """

    if hvac_mode == HVACMode.HEAT:
        return "heat"
    if hvac_mode == HVACMode.DRY:
        return "dry"
    if hvac_mode == HVACMode.FAN_ONLY:
        return "fan_only"
    if hvac_mode == HVACMode.HEAT_COOL:
        return "heat_cool"

    return "cool"
