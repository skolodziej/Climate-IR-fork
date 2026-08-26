"""Climate platform for MHI IR Climate.

The entity is protocol agnostic: every vocabulary, rule, and quirk comes from
the profile selected for the config entry. See `protocols/base.py`.
"""

from __future__ import annotations

from typing import Any, cast

from homeassistant.components import infrared
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_HORIZONTAL_MODE,
    ATTR_SWING_MODE,
    HVACMode,
    PRESET_BOOST,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    PRECISION_TENTHS,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_INFRARED_EMITTER_ENTITY_ID,
    ATTR_LAST_ON_HVAC_MODE,
    ATTR_LAST_SWING_HORIZONTAL_MODE,
    ATTR_LAST_SWING_MODE,
    ATTR_MODEL,
    ATTR_PROTOCOL,
    CONF_BASE_FRAME_HEX,
    CONF_EMITTER_ENTITY_ID,
    CONF_HUMIDITY_SENSOR,
    CONF_PROTOCOL,
    CONF_TEMPERATURE_SENSOR,
    DOMAIN,
)
from .protocols import (
    ClimateProfile,
    ClimateState,
    EntityState,
    get_profile,
    hvac_mode_to_protocol_mode,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entity for a config entry."""

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    entity = MHIIRClimateEntity(hass, entry, runtime_data)
    runtime_data["climate_entity"] = entity
    async_add_entities([entity])


class MHIIRClimateEntity(ClimateEntity, RestoreEntity):
    """Optimistic MHI climate entity backed by an infrared emitter."""

    _attr_has_entity_name = False
    _attr_precision = PRECISION_TENTHS
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        data: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""

        self.hass = hass
        self._entry = entry
        self._runtime_data = data
        config = data["config"]
        profile: ClimateProfile = data.get("profile") or get_profile(
            config.get(CONF_PROTOCOL)
        )
        self._profile = profile
        self._config = config
        self._emitter_entity_id = config[CONF_EMITTER_ENTITY_ID]
        self._temperature_sensor_entity_id = _optional_entity_id(
            config.get(CONF_TEMPERATURE_SENSOR)
        )
        self._humidity_sensor_entity_id = _optional_entity_id(
            config.get(CONF_HUMIDITY_SENSOR)
        )
        self._name = config[CONF_NAME]
        self._last_on_hvac_mode = HVACMode.COOL
        self._last_swing_mode: str | None = None
        self._last_swing_horizontal_mode: str | None = None
        self._cancel_boost_reset = None

        self._attr_name = self._name
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": profile.manufacturer,
            "model": profile.device_model,
            "name": self._name,
        }
        self._attr_supported_features = _supported_features(profile)
        self._attr_min_temp = profile.min_temperature
        self._attr_max_temp = profile.max_temperature
        self._attr_target_temperature_step = profile.temperature_step
        self._attr_hvac_modes = list(profile.hvac_modes)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_modes = list(profile.fan_modes)
        self._attr_fan_mode = profile.default_fan_mode
        self._attr_preset_modes = list(profile.preset_modes)
        self._attr_preset_mode = profile.default_preset_mode
        self._attr_swing_modes = list(profile.swing_modes)
        self._attr_swing_mode = profile.default_swing_mode
        self._attr_swing_horizontal_modes = list(profile.swing_horizontal_modes)
        self._attr_swing_horizontal_mode = profile.default_swing_horizontal_mode
        self._attr_target_temperature = profile.default_temperature
        self._attr_current_temperature = None
        self._attr_current_humidity = None

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to sensor/emitter changes."""

        await super().async_added_to_hass()
        await self._async_restore_previous_state()
        self.async_on_remove(self._cancel_boost_preset_reset)

        tracked_entity_ids = [self._emitter_entity_id]
        if self._temperature_sensor_entity_id:
            tracked_entity_ids.append(self._temperature_sensor_entity_id)
        if self._humidity_sensor_entity_id:
            tracked_entity_ids.append(self._humidity_sensor_entity_id)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                tracked_entity_ids,
                self._async_tracked_state_changed,
            )
        )

    @property
    def available(self) -> bool:
        """Return whether the configured infrared emitter is available."""

        state = self.hass.states.get(self._emitter_entity_id)
        return state is not None and state.state != STATE_UNAVAILABLE

    @property
    def current_temperature(self) -> float | None:
        """Return the current room temperature."""

        return self._read_sensor_float(
            self._temperature_sensor_entity_id,
            cast(float | None, self._attr_current_temperature),
        )

    @property
    def current_humidity(self) -> int | None:
        """Return the current room humidity."""

        humidity = self._read_sensor_float(
            self._humidity_sensor_entity_id,
            cast(float | None, self._attr_current_humidity),
        )
        return None if humidity is None else round(humidity)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return integration-specific state attributes."""

        return {
            ATTR_INFRARED_EMITTER_ENTITY_ID: self._emitter_entity_id,
            ATTR_LAST_ON_HVAC_MODE: self._last_on_hvac_mode.value,
            ATTR_LAST_SWING_MODE: self._last_swing_mode,
            ATTR_LAST_SWING_HORIZONTAL_MODE: self._last_swing_horizontal_mode,
            ATTR_MODEL: self._profile.device_model,
            ATTR_PROTOCOL: self._profile.key,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode | str) -> None:
        """Set HVAC mode and send a matching IR command."""

        mode = _coerce_hvac_mode(hvac_mode)
        if mode not in self._attr_hvac_modes:
            raise HomeAssistantError(f"Unsupported HVAC mode: {hvac_mode}")

        previous_mode = _coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode))
        powering_off = mode == HVACMode.OFF and previous_mode != HVACMode.OFF

        self._attr_hvac_mode = mode
        if mode != HVACMode.OFF:
            self._last_on_hvac_mode = mode
        if not self._profile.preset_available(
            cast(str, self._attr_preset_mode), mode
        ):
            self._set_preset_mode_without_ir(PRESET_NONE)
        self._sync_preset_temperature()
        self._reconcile(changed=ATTR_HVAC_MODE)

        extras = (
            dict(self._profile.power_off_extras(previous_mode, self._options()))
            if powering_off
            else {}
        )

        self.async_write_ha_state()
        await self._async_send_current_state(
            off_hvac_mode=previous_mode if powering_off else None,
            extras=extras,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature and send an IR command if the unit is on."""

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._release_temperature_locking_preset()
            self._attr_target_temperature = self._clamp_temperature(temperature)

        if hvac_mode := kwargs.get(ATTR_HVAC_MODE):
            await self.async_set_hvac_mode(hvac_mode)
            return

        self._reconcile(changed=ATTR_TEMPERATURE)
        self.async_write_ha_state()
        await self._async_send_if_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""

        try:
            preset_mode = self._profile.normalize_preset_mode(preset_mode)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        if preset_mode not in self._attr_preset_modes:
            raise HomeAssistantError(f"Unsupported preset mode: {preset_mode}")

        required_mode = self._profile.hvac_mode_for_preset(
            preset_mode,
            _coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode)),
        )
        if required_mode is not None:
            self._attr_hvac_mode = required_mode
            self._last_on_hvac_mode = required_mode

        if preset_mode != PRESET_NONE and not self._profile.preset_available(
            preset_mode,
            _coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode)),
        ):
            raise HomeAssistantError(
                f"Preset mode {preset_mode} is not available in "
                f"{self._attr_hvac_mode}"
            )

        self._set_preset_mode_without_ir(preset_mode)
        self._reconcile(changed=ATTR_PRESET_MODE)
        self.async_write_ha_state()
        await self._async_send_if_on()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed and send an IR command if the unit is on."""

        if fan_mode not in self._attr_fan_modes:
            raise HomeAssistantError(f"Unsupported fan mode: {fan_mode}")

        self._attr_fan_mode = fan_mode
        self._reconcile(changed=ATTR_FAN_MODE)
        self.async_write_ha_state()
        await self._async_send_if_on()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set vertical swing mode and send an IR command if the unit is on."""

        if swing_mode not in self._attr_swing_modes:
            raise HomeAssistantError(f"Unsupported swing mode: {swing_mode}")

        if error := self._profile.swing_mode_error(swing_mode, self._entity_state()):
            raise HomeAssistantError(error)

        self._attr_swing_mode = swing_mode
        self._reconcile(changed=ATTR_SWING_MODE)
        self.async_write_ha_state()
        await self._async_send_if_on()

    async def async_set_swing_horizontal_mode(
        self,
        swing_horizontal_mode: str,
    ) -> None:
        """Set horizontal swing mode and send an IR command if the unit is on."""

        if swing_horizontal_mode not in self._attr_swing_horizontal_modes:
            raise HomeAssistantError(
                f"Unsupported horizontal swing mode: {swing_horizontal_mode}"
            )

        if error := self._profile.swing_horizontal_mode_error(
            swing_horizontal_mode,
            self._entity_state(),
        ):
            raise HomeAssistantError(error)

        self._attr_swing_horizontal_mode = swing_horizontal_mode
        self._reconcile(changed=ATTR_SWING_HORIZONTAL_MODE)
        self.async_write_ha_state()
        await self._async_send_if_on()

    async def async_turn_on(self) -> None:
        """Turn on using the last active mode."""

        await self.async_set_hvac_mode(self._last_on_hvac_mode)

    async def async_turn_off(self) -> None:
        """Turn the AC off."""

        await self.async_set_hvac_mode(HVACMode.OFF)

    async def _async_restore_previous_state(self) -> None:
        """Restore optimistic climate state from the recorder."""

        previous_state = await self.async_get_last_state()
        if previous_state is None:
            return

        profile = self._profile
        attributes = previous_state.attributes

        try:
            previous_hvac_mode = HVACMode(previous_state.state)
        except ValueError:
            previous_hvac_mode = HVACMode.OFF

        if previous_hvac_mode in profile.hvac_modes:
            self._attr_hvac_mode = previous_hvac_mode
            if previous_hvac_mode != HVACMode.OFF:
                self._last_on_hvac_mode = previous_hvac_mode

        if last_on_mode := attributes.get(ATTR_LAST_ON_HVAC_MODE):
            try:
                last_on_hvac_mode = HVACMode(last_on_mode)
            except ValueError:
                last_on_hvac_mode = HVACMode.COOL
            if last_on_hvac_mode != HVACMode.OFF:
                self._last_on_hvac_mode = last_on_hvac_mode

        if (temperature := attributes.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = self._clamp_temperature(temperature)

        if (fan_mode := attributes.get(ATTR_FAN_MODE)) in profile.fan_modes:
            self._attr_fan_mode = fan_mode

        if (preset_mode := attributes.get(ATTR_PRESET_MODE)) is not None:
            try:
                self._attr_preset_mode = profile.normalize_preset_mode(preset_mode)
            except ValueError:
                pass

        for attribute, stored in (
            (ATTR_LAST_SWING_MODE, profile.swing_modes),
            (ATTR_LAST_SWING_HORIZONTAL_MODE, profile.swing_horizontal_modes),
        ):
            value = attributes.get(attribute)
            if value in stored and value != profile.default_swing_mode:
                if attribute == ATTR_LAST_SWING_MODE:
                    self._last_swing_mode = value
                else:
                    self._last_swing_horizontal_mode = value

        if (swing_mode := attributes.get(ATTR_SWING_MODE)) in profile.swing_modes:
            self._attr_swing_mode = swing_mode

        horizontal_restored = attributes.get(ATTR_SWING_HORIZONTAL_MODE)
        if horizontal_restored in profile.swing_horizontal_modes:
            self._attr_swing_horizontal_mode = horizontal_restored
        elif profile.supports_horizontal_swing:
            # Let the profile fill it in from the remembered position.
            self._attr_swing_horizontal_mode = None

        if not profile.preset_available(
            cast(str, self._attr_preset_mode), self._attr_hvac_mode
        ):
            self._set_preset_mode_without_ir(PRESET_NONE)
        elif self._attr_preset_mode == PRESET_BOOST:
            self._schedule_boost_preset_reset()

        self._reconcile()

        if (
            current_temperature := attributes.get(ATTR_CURRENT_TEMPERATURE)
        ) is not None:
            self._attr_current_temperature = _maybe_float(current_temperature)

        if (current_humidity := attributes.get(ATTR_CURRENT_HUMIDITY)) is not None:
            self._attr_current_humidity = _maybe_float(current_humidity)

    @callback
    def _async_tracked_state_changed(self, event: Any) -> None:
        """Update HA state when a configured source entity changes."""

        self.async_write_ha_state()

    # --- profile bridge -----------------------------------------------------
    def _entity_state(self, changed: str | None = None) -> EntityState:
        """Return the user-visible state as the profile sees it."""

        return EntityState(
            hvac_mode=_coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode)),
            temperature=self._clamp_temperature(
                self._attr_target_temperature or self._profile.default_temperature
            ),
            fan_mode=cast(str, self._attr_fan_mode),
            preset_mode=cast(str, self._attr_preset_mode),
            swing_mode=cast(str | None, self._attr_swing_mode),
            swing_horizontal_mode=cast(
                str | None, self._attr_swing_horizontal_mode
            ),
            last_swing_mode=self._last_swing_mode,
            last_swing_horizontal_mode=self._last_swing_horizontal_mode,
            changed=changed,
        )

    def _reconcile(self, changed: str | None = None) -> None:
        """Let the profile enforce its rules on the current state."""

        state = self._entity_state(changed)
        self._profile.adjust_state(state)

        self._attr_hvac_mode = state.hvac_mode
        self._attr_target_temperature = state.temperature
        self._attr_fan_mode = state.fan_mode
        self._attr_preset_mode = state.preset_mode
        self._attr_swing_mode = state.swing_mode
        self._attr_swing_horizontal_mode = state.swing_horizontal_mode
        self._last_swing_mode = state.last_swing_mode
        self._last_swing_horizontal_mode = state.last_swing_horizontal_mode

    def _options(self) -> dict[str, Any]:
        """Return the persistent device-control values."""

        return self._runtime_data.setdefault("options", {})

    async def _async_send_if_on(self) -> None:
        """Send the current state unless the entity is off."""

        if self._attr_hvac_mode != HVACMode.OFF:
            await self._async_send_current_state()

    async def _async_send_current_state(
        self,
        *,
        off_hvac_mode: HVACMode | None = None,
        extras: dict[str, Any] | None = None,
    ) -> None:
        """Send an IR command representing the entity's current target state."""

        power_on = self._attr_hvac_mode != HVACMode.OFF
        command_hvac_mode = (
            self._attr_hvac_mode
            if power_on
            else off_hvac_mode or self._last_on_hvac_mode
        )
        state = ClimateState(
            mode=hvac_mode_to_protocol_mode(command_hvac_mode),
            temperature=self._clamp_temperature(
                self._attr_target_temperature or self._profile.default_temperature
            ),
            power_on=power_on,
            fan_mode=cast(str, self._attr_fan_mode),
            preset_mode=cast(str, self._attr_preset_mode),
            swing_mode=cast(str | None, self._attr_swing_mode),
            swing_horizontal_mode=cast(
                str | None, self._attr_swing_horizontal_mode
            ),
            last_swing_mode=self._last_swing_mode,
            last_swing_horizontal_mode=self._last_swing_horizontal_mode,
            config=self._config,
            options=self._options(),
            extras=extras or {},
        )

        try:
            command = self._profile.build_command(state)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        await infrared.async_send_command(
            self.hass,
            self._emitter_entity_id,
            command,
            context=self._context,
        )

    def _read_sensor_float(
        self,
        entity_id: str | None,
        fallback: float | None,
    ) -> float | None:
        """Read a numeric sensor state."""

        if entity_id is None:
            return fallback

        state = self.hass.states.get(entity_id)
        if state is None:
            return fallback

        return _state_float(state, fallback)

    def _set_preset_mode_without_ir(self, preset_mode: str) -> None:
        """Update preset mode without sending an IR command."""

        self._attr_preset_mode = preset_mode
        self._sync_preset_temperature()
        if preset_mode == PRESET_BOOST and self._profile.boost_reset_seconds:
            self._schedule_boost_preset_reset()
        else:
            self._cancel_boost_preset_reset()

    def _sync_preset_temperature(self) -> None:
        """Mirror the setpoint the remote forces for the active preset."""

        forced = self._profile.preset_temperature(
            cast(str, self._attr_preset_mode),
            _coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode)),
        )
        if forced is not None:
            self._attr_target_temperature = forced

    def _release_temperature_locking_preset(self) -> None:
        """Clear a preset that owns the setpoint before applying a new one."""

        if self._attr_preset_mode in self._profile.temperature_locking_presets:
            self._attr_preset_mode = PRESET_NONE
            self._cancel_boost_preset_reset()

    def _schedule_boost_preset_reset(self) -> None:
        """Schedule Boost preset to clear in Home Assistant state only."""

        if not self._profile.boost_reset_seconds:
            return

        self._cancel_boost_preset_reset()
        self._cancel_boost_reset = async_call_later(
            self.hass,
            self._profile.boost_reset_seconds,
            self._boost_preset_reset_elapsed,
        )

    @callback
    def _boost_preset_reset_elapsed(self, _now) -> None:
        """Clear Boost preset without sending IR."""

        self._cancel_boost_reset = None
        if self._attr_preset_mode == PRESET_BOOST:
            self._attr_preset_mode = PRESET_NONE
            self.async_write_ha_state()

    def _cancel_boost_preset_reset(self) -> None:
        """Cancel any pending Boost reset callback."""

        if self._cancel_boost_reset is not None:
            self._cancel_boost_reset()
            self._cancel_boost_reset = None

    def _clamp_temperature(self, value: Any) -> int:
        """Clamp and round a target temperature to the profile's range."""

        temperature = round(float(value))
        return min(
            self._profile.max_temperature,
            max(self._profile.min_temperature, temperature),
        )

    # --- called by the device-control platforms -----------------------------
    async def async_control_changed(self, key: str, value: Any) -> None:
        """Send whatever a changed device control requires."""

        if self._profile.should_send_after_control_change(
            key,
            value,
            _coerce_hvac_mode(cast(HVACMode | str, self._attr_hvac_mode)),
        ):
            await self._async_send_current_state()

    async def async_send_one_shot(self, key: str, value: Any = True) -> None:
        """Send a single command carrying a one-shot value."""

        await self._async_send_current_state(extras={key: value})

    async def async_send_current_state_if_on(self) -> None:
        """Send the current IR state when the climate entity is on."""

        await self._async_send_if_on()

    async def async_force_send_current_state(self) -> None:
        """Force-send the current IR state."""

        await self._async_send_current_state()

    @property
    def hvac_is_off(self) -> bool:
        """Return whether the entity is currently off."""

        return self._attr_hvac_mode == HVACMode.OFF


def _supported_features(profile: ClimateProfile) -> ClimateEntityFeature:
    """Return the features a profile can actually drive."""

    features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    if profile.fan_modes:
        features |= ClimateEntityFeature.FAN_MODE
    if profile.supports_swing:
        features |= ClimateEntityFeature.SWING_MODE
    if profile.supports_horizontal_swing:
        features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

    return features


def _optional_entity_id(value: Any) -> str | None:
    """Normalize optional entity IDs from config data."""

    if value in (None, ""):
        return None
    return str(value)


def _coerce_hvac_mode(value: HVACMode | str) -> HVACMode:
    """Coerce a service value to HVACMode."""

    try:
        return HVACMode(value)
    except ValueError as err:
        raise HomeAssistantError(f"Unsupported HVAC mode: {value}") from err


def _state_float(state: State, fallback: float | None) -> float | None:
    """Convert a state object to float when available."""

    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return fallback

    return _maybe_float(state.state, fallback)


def _maybe_float(value: Any, fallback: float | None = None) -> float | None:
    """Convert a value to float or return a fallback."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
