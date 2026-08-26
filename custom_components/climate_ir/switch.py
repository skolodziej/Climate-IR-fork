"""Switch entities for Climate IR.

Built from the SwitchControls a protocol profile declares.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .protocols import SwitchControl


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches the profile declares."""

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ClimateIRSwitch(entry, runtime_data, control)
        for control in runtime_data["profile"].controls()
        if isinstance(control, SwitchControl)
    )


class ClimateIRSwitch(SwitchEntity, RestoreEntity):
    """A profile-declared switch on the device page."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        runtime_data: dict[str, Any],
        control: SwitchControl,
    ) -> None:
        """Initialize the switch."""

        self._runtime_data = runtime_data
        self._control = control
        self._attr_name = control.name
        self._attr_is_on = bool(
            self._options().get(control.key, control.default)
        )
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{control.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    def _options(self) -> dict[str, Any]:
        return self._runtime_data.setdefault("options", {})

    async def async_added_to_hass(self) -> None:
        """Restore the switch value."""

        await super().async_added_to_hass()

        previous_state = await self.async_get_last_state()
        if previous_state is not None:
            self._attr_is_on = previous_state.state == STATE_ON

        self._options()[self._control.key] = self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the control."""

        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the control."""

        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Set the value and send any command the profile requires."""

        self._attr_is_on = enabled
        self._options()[self._control.key] = enabled
        self.async_write_ha_state()

        climate_entity = self._runtime_data.get("climate_entity")
        if climate_entity is not None:
            await climate_entity.async_control_changed(self._control.key, enabled)
