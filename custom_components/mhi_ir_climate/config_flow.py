"""Config flow for MHI IR Climate."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import infrared
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    CONF_BASE_FRAME_HEX,
    CONF_EMITTER_ENTITY_ID,
    CONF_HUMIDITY_SENSOR,
    CONF_PROTOCOL,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_NAME,
    DEFAULT_PROTOCOL,
    DOMAIN,
    PROTOCOLS,
)
from .entity_validation import async_is_sensor_entity_valid
from .ir_protocol import DEFAULT_BASE_FRAME_HEX
from .profiles import ClimateProfile, get_profile


class MHIIRClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MHI IR Climate."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._protocol = DEFAULT_PROTOCOL

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""

        return MHIIRClimateOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Pick the remote family the indoor unit uses."""

        if not set(infrared.async_get_emitters(self.hass)):
            return self.async_abort(reason="no_emitters")

        if user_input is not None:
            self._protocol = user_input[CONF_PROTOCOL]
            return await self.async_step_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PROTOCOL,
                        default=DEFAULT_PROTOCOL,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(PROTOCOLS),
                            translation_key=CONF_PROTOCOL,
                            mode=selector.SelectSelectorMode.LIST,
                        ),
                    ),
                }
            ),
        )

    async def async_step_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create an MHI IR climate entity."""

        emitters = set(infrared.async_get_emitters(self.hass))
        if not emitters:
            return self.async_abort(reason="no_emitters")

        profile = get_profile(self._protocol)
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_input(self.hass, user_input, emitters, profile)
            if not errors:
                name = user_input[CONF_NAME]
                unique_id = f"{slugify(name)}_{user_input[CONF_EMITTER_ENTITY_ID]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={**user_input, CONF_PROTOCOL: self._protocol},
                )

        return self.async_show_form(
            step_id="settings",
            data_schema=_schema(profile),
            errors=errors,
            description_placeholders={"model": profile.device_model},
        )


class MHIIRClimateOptionsFlow(config_entries.OptionsFlow):
    """Handle options for MHI IR Climate."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Update options."""

        data = {**self.config_entry.data, **self.config_entry.options}
        profile = get_profile(data.get(CONF_PROTOCOL))
        emitters = set(infrared.async_get_emitters(self.hass))

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_input(self.hass, user_input, emitters, profile)
            if not errors:
                for key in (CONF_TEMPERATURE_SENSOR, CONF_HUMIDITY_SENSOR):
                    user_input.setdefault(key, None)
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                profile,
                user_input if user_input is not None else data,
            ),
            errors=errors,
            description_placeholders={"model": profile.device_model},
        )


def _validate_input(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    emitters: set[str],
    profile: ClimateProfile,
) -> dict[str, str]:
    """Validate config flow input."""

    errors: dict[str, str] = {}

    if user_input[CONF_EMITTER_ENTITY_ID] not in emitters:
        errors[CONF_EMITTER_ENTITY_ID] = "invalid_emitter"

    for key in (CONF_TEMPERATURE_SENSOR, CONF_HUMIDITY_SENSOR):
        entity_id = user_input.get(key)
        if entity_id and not async_is_sensor_entity_valid(hass, str(entity_id)):
            errors[key] = "invalid_sensor"

    if profile.requires_base_frame:
        try:
            profile.validate_base_frame(user_input[CONF_BASE_FRAME_HEX])
        except ValueError:
            errors[CONF_BASE_FRAME_HEX] = "invalid_base_frame"

    return errors


def _schema(
    profile: ClimateProfile,
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Return the flow schema for a protocol profile."""

    defaults = defaults or {}
    emitter_default = defaults.get(CONF_EMITTER_ENTITY_ID)
    emitter_marker = (
        vol.Required(CONF_EMITTER_ENTITY_ID, default=emitter_default)
        if emitter_default
        else vol.Required(CONF_EMITTER_ENTITY_ID)
    )
    schema: dict[vol.Marker, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
        emitter_marker: selector.EntitySelector(
            selector.EntitySelectorConfig(domain="infrared"),
        ),
    }

    if profile.requires_base_frame:
        schema[
            vol.Required(
                CONF_BASE_FRAME_HEX,
                default=defaults.get(CONF_BASE_FRAME_HEX, DEFAULT_BASE_FRAME_HEX),
            )
        ] = str

    _add_optional_entity_selector(schema, CONF_TEMPERATURE_SENSOR, defaults)
    _add_optional_entity_selector(schema, CONF_HUMIDITY_SENSOR, defaults)

    return vol.Schema(schema)


def _add_optional_entity_selector(
    schema: dict[vol.Marker, Any],
    key: str,
    defaults: dict[str, Any],
) -> None:
    """Add an optional sensor entity selector to a schema."""

    default = defaults.get(key)
    marker = (
        vol.Optional(key, description={"suggested_value": default})
        if default
        else vol.Optional(key)
    )
    schema[marker] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor"),
    )
