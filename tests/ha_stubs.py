"""Home Assistant stubs shared by the entity-level tests.

The integration targets a Home Assistant runtime; these stubs provide just
enough of it to import the platform modules and drive them directly.
"""

from __future__ import annotations

from enum import Enum, IntFlag
import importlib
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import AsyncMock


def _module(name: str, *, package: bool = False, **attributes: object) -> ModuleType:
    module = ModuleType(name)
    if package:
        module.__path__ = []
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    sys.modules[name] = module
    return module


class HVACMode(str, Enum):
    OFF = "off"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"
    HEAT_COOL = "heat_cool"


class ClimateEntityFeature(IntFlag):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 2
    PRESET_MODE = 4
    SWING_MODE = 8
    SWING_HORIZONTAL_MODE = 16
    TURN_ON = 32
    TURN_OFF = 64


class ClimateEntity:
    _context = None

    async def async_added_to_hass(self) -> None:
        return None

    def async_on_remove(self, callback: object) -> object:
        return callback

    def async_write_ha_state(self) -> None:
        return None


class RestoreEntity:
    async def async_get_last_state(self) -> object | None:
        return None


class _PlatformEntity:
    """Shared stand-in for the select, switch, and button entity bases."""

    _attr_device_info: object = None
    _attr_unique_id: str = ""

    async def async_added_to_hass(self) -> None:
        return None

    def async_write_ha_state(self) -> None:
        return None


class SelectEntity(_PlatformEntity):
    _attr_current_option: str | None = None


class SwitchEntity(_PlatformEntity):
    _attr_is_on: bool = False


class ButtonEntity(_PlatformEntity):
    pass


class EntityCategory(str, Enum):
    CONFIG = "config"


class HomeAssistantError(Exception):
    """Minimal Home Assistant service error."""


class Platform(str, Enum):
    CLIMATE = "climate"
    SELECT = "select"
    BUTTON = "button"
    SWITCH = "switch"


class UnitOfTemperature(str, Enum):
    CELSIUS = "°C"


class _Command:
    def __init__(self, **kwargs: int) -> None:
        self.modulation = kwargs.get("modulation")
        self.repeat_count = kwargs.get("repeat_count")


def _cancel_callback() -> None:
    return None


def _async_call_later(*_args: object, **_kwargs: object):
    return _cancel_callback


def _install_home_assistant_stubs() -> None:
    _module("homeassistant", package=True)
    _module("homeassistant.components", package=True)
    _module(
        "homeassistant.components.infrared",
        async_send_command=AsyncMock(),
    )
    _module(
        "homeassistant.components.climate",
        ClimateEntity=ClimateEntity,
        ClimateEntityFeature=ClimateEntityFeature,
    )
    _module("homeassistant.components.select", SelectEntity=SelectEntity)
    _module("homeassistant.components.switch", SwitchEntity=SwitchEntity)
    _module("homeassistant.components.button", ButtonEntity=ButtonEntity)
    _module(
        "homeassistant.components.climate.const",
        ATTR_CURRENT_HUMIDITY="current_humidity",
        ATTR_CURRENT_TEMPERATURE="current_temperature",
        ATTR_FAN_MODE="fan_mode",
        ATTR_HVAC_MODE="hvac_mode",
        ATTR_PRESET_MODE="preset_mode",
        ATTR_SWING_HORIZONTAL_MODE="swing_horizontal_mode",
        ATTR_SWING_MODE="swing_mode",
        HVACMode=HVACMode,
        PRESET_BOOST="boost",
        PRESET_NONE="none",
    )
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module(
        "homeassistant.const",
        ATTR_TEMPERATURE="temperature",
        CONF_NAME="name",
        PRECISION_TENTHS=0.1,
        STATE_ON="on",
        STATE_UNAVAILABLE="unavailable",
        STATE_UNKNOWN="unknown",
        UnitOfTemperature=UnitOfTemperature,
        Platform=Platform,
    )
    _module(
        "homeassistant.core",
        HomeAssistant=object,
        State=object,
        callback=lambda function: function,
    )
    _module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
    _module("homeassistant.helpers", package=True)
    _module("homeassistant.helpers.entity", EntityCategory=EntityCategory)
    _module(
        "homeassistant.helpers.entity_platform",
        AddEntitiesCallback=object,
    )
    _module(
        "homeassistant.helpers.event",
        async_call_later=_async_call_later,
        async_track_state_change_event=lambda *_args, **_kwargs: _cancel_callback,
    )
    _module("homeassistant.helpers.restore_state", RestoreEntity=RestoreEntity)

    infrared_protocols = _module("infrared_protocols", package=True)
    commands = _module("infrared_protocols.commands", Command=_Command)
    infrared_protocols.commands = commands


REPOSITORY_ROOT = Path(__file__).parents[1]
_install_home_assistant_stubs()
custom_components = _module("custom_components", package=True)
custom_components.__path__ = [str(REPOSITORY_ROOT / "custom_components")]
mhi_package = _module("custom_components.mhi_ir_climate", package=True)
mhi_package.__path__ = [
    str(REPOSITORY_ROOT / "custom_components" / "mhi_ir_climate")
]
climate = importlib.import_module("custom_components.mhi_ir_climate.climate")

__all__ = [
    "ClimateEntityFeature",
    "HVACMode",
    "HomeAssistantError",
    "button",
    "climate",
    "fd_protocol",
    "infrared",
    "protocols",
    "select",
    "switch",
]

infrared = sys.modules["homeassistant.components.infrared"]
fd_protocol = importlib.import_module(
    "custom_components.mhi_ir_climate.fd_protocol"
)
protocols = importlib.import_module("custom_components.mhi_ir_climate.protocols")
button = importlib.import_module("custom_components.mhi_ir_climate.button")
select = importlib.import_module("custom_components.mhi_ir_climate.select")
switch = importlib.import_module("custom_components.mhi_ir_climate.switch")
