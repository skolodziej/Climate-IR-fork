"""Validation helpers for entities referenced by configuration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components import infrared
from homeassistant.const import ATTR_RESTORED
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_EMITTER_ENTITY_ID,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMPERATURE_SENSOR,
)


@callback
def async_configured_entity_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the configured entity IDs in display order."""

    entity_ids: list[str] = []
    for key in (
        CONF_EMITTER_ENTITY_ID,
        CONF_TEMPERATURE_SENSOR,
        CONF_HUMIDITY_SENSOR,
    ):
        if entity_id := _optional_entity_id(config.get(key)):
            if entity_id not in entity_ids:
                entity_ids.append(entity_id)

    return tuple(entity_ids)


@callback
def async_get_invalid_configured_entities(
    hass: HomeAssistant,
    config: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return configured entity IDs that are no longer actively provided."""

    invalid_entity_ids: list[str] = []
    emitter_entity_id = _optional_entity_id(config.get(CONF_EMITTER_ENTITY_ID))
    if emitter_entity_id and emitter_entity_id not in set(
        infrared.async_get_emitters(hass)
    ):
        invalid_entity_ids.append(emitter_entity_id)

    for key in (CONF_TEMPERATURE_SENSOR, CONF_HUMIDITY_SENSOR):
        sensor_entity_id = _optional_entity_id(config.get(key))
        if sensor_entity_id and not async_is_sensor_entity_valid(
            hass, sensor_entity_id
        ):
            invalid_entity_ids.append(sensor_entity_id)

    return tuple(dict.fromkeys(invalid_entity_ids))


@callback
def async_is_sensor_entity_valid(hass: HomeAssistant, entity_id: str) -> bool:
    """Return whether a sensor entity is actively provided."""

    if not entity_id.startswith("sensor."):
        return False

    state = hass.states.get(entity_id)
    return state is not None and not state.attributes.get(ATTR_RESTORED, False)


def _optional_entity_id(value: Any) -> str | None:
    """Normalize an optional configured entity ID."""

    if value in (None, ""):
        return None
    return str(value)
