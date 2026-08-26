"""Constants for the Climate IR integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "climate_ir"
PLATFORMS = [Platform.CLIMATE, Platform.SELECT, Platform.BUTTON, Platform.SWITCH]

CONF_BASE_FRAME_HEX = "base_frame_hex"
CONF_EMITTER_ENTITY_ID = "emitter_entity_id"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_PROTOCOL = "protocol"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"

DEFAULT_NAME = "MHI Air Conditioner"


ATTR_INFRARED_EMITTER_ENTITY_ID = "infrared_emitter_entity_id"
ATTR_LAST_ON_HVAC_MODE = "last_on_hvac_mode"
ATTR_LAST_SWING_HORIZONTAL_MODE = "last_swing_horizontal_mode"
ATTR_LAST_SWING_MODE = "last_swing_mode"
ATTR_MODEL = "model"
ATTR_PROTOCOL = "protocol"
