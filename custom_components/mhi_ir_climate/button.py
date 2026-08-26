"""Button entities for MHI IR Climate.

Every family gets the force-send button; the rest come from the ButtonControls
a protocol profile declares.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .protocols import ButtonControl


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""

    runtime_data = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = [MHIIRForceSendButton(entry, runtime_data)]
    entities.extend(
        MHIIROneShotButton(entry, runtime_data, control)
        for control in runtime_data["profile"].controls()
        if isinstance(control, ButtonControl)
    )

    async_add_entities(entities)


class _MHIIRButton(ButtonEntity):
    """Shared plumbing for the integration's buttons."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def _climate_entity(self) -> Any:
        climate_entity = self._runtime_data.get("climate_entity")
        if climate_entity is None:
            raise HomeAssistantError("MHI IR climate entity is not ready")

        return climate_entity


class MHIIRForceSendButton(_MHIIRButton):
    """Force-send the current climate IR command."""

    _attr_name = "Force send IR command"

    def __init__(self, entry: ConfigEntry, runtime_data: dict[str, Any]) -> None:
        """Initialize the button."""

        self._runtime_data = runtime_data
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_force_send"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    async def async_press(self) -> None:
        """Force-send the current IR command."""

        await self._climate_entity().async_force_send_current_state()


class MHIIROneShotButton(_MHIIRButton):
    """A profile-declared button that sends one command."""

    def __init__(
        self,
        entry: ConfigEntry,
        runtime_data: dict[str, Any],
        control: ButtonControl,
    ) -> None:
        """Initialize the button."""

        self._runtime_data = runtime_data
        self._control = control
        self._attr_name = control.name
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{control.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    async def async_press(self) -> None:
        """Send the single command this button stands for."""

        climate_entity = self._climate_entity()
        if self._control.requires_power_on and climate_entity.hvac_is_off:
            raise HomeAssistantError(
                f"{self._control.name} needs the AC to be on"
            )

        await climate_entity.async_send_one_shot(
            self._control.extra or self._control.key
        )
