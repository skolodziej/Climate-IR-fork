"""Select entities for Climate IR.

Built from the SelectControls a protocol profile declares, so a new family
gets its device-page selects without touching this file.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .protocols import SelectControl


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the selects the profile declares."""

    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ClimateIRSelect(entry, runtime_data, control)
        for control in runtime_data["profile"].controls()
        if isinstance(control, SelectControl)
    )


class ClimateIRSelect(SelectEntity, RestoreEntity):
    """A profile-declared select on the device page."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        runtime_data: dict[str, Any],
        control: SelectControl,
    ) -> None:
        """Initialize the select."""

        self._runtime_data = runtime_data
        self._control = control
        self._attr_name = control.name
        self._attr_options = list(control.options)
        self._attr_current_option = self._options().get(
            control.key, control.default
        )
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{control.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    def _options(self) -> dict[str, Any]:
        return self._runtime_data.setdefault("options", {})

    async def async_added_to_hass(self) -> None:
        """Restore the selected value."""

        await super().async_added_to_hass()

        previous_state = await self.async_get_last_state()
        if previous_state is not None and previous_state.state in self._attr_options:
            self._attr_current_option = previous_state.state

        self._options()[self._control.key] = self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Select a new value and send whatever the profile requires."""

        if option not in self._attr_options:
            raise HomeAssistantError(
                f"Unsupported {self._control.name}: {option}"
            )
        if option == self._attr_current_option and self._control.one_shot:
            return

        climate_entity = self._runtime_data.get("climate_entity")
        if climate_entity is None:
            raise HomeAssistantError("MHI IR climate entity is not ready")

        if self._control.requires_power_off and not climate_entity.hvac_is_off:
            raise HomeAssistantError(
                f"{self._control.name} can only be changed while the AC is off"
            )

        if self._control.one_shot:
            await climate_entity.async_send_one_shot(self._control.key, option)
        else:
            self._options()[self._control.key] = option
            await climate_entity.async_control_changed(self._control.key, option)

        self._attr_current_option = option
        self._options()[self._control.key] = option
        self.async_write_ha_state()
