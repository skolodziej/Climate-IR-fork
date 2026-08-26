"""MHI IR Climate custom integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_RESTORED,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_PROTOCOL, DOMAIN, PLATFORMS
from .entity_validation import (
    async_configured_entity_ids,
    async_get_invalid_configured_entities,
)
from .protocols import get_profile

ISSUE_INVALID_CONFIGURED_ENTITIES = "invalid_configured_entities"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MHI IR Climate from a config entry."""

    config = _entry_config(entry)
    profile = get_profile(config.get(CONF_PROTOCOL))
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "climate_entity": None,
        "config": config,
        "profile": profile,
        # Persistent device-control values, keyed by the profile's control keys.
        "options": {
            control.key: control.default
            for control in profile.controls()
            if getattr(control, "default", None) is not None
        },
    }

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_setup_entity_validation(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after options change."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up the repair issue when a config entry is removed."""

    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry))


@callback
def _async_setup_entity_validation(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Set up validation for entities referenced by a config entry."""

    @callback
    def _async_entity_registry_updated(event: Event[Any]) -> None:
        configured_entity_ids = _configured_entity_ids(entry)
        if (
            event.data.get("entity_id") not in configured_entity_ids
            and event.data.get("old_entity_id") not in configured_entity_ids
        ):
            return

        _async_validate_configured_entities(hass, entry)

    @callback
    def _async_state_changed(event: Event[Any]) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        old_restored = old_state is not None and old_state.attributes.get(
            ATTR_RESTORED, False
        )
        new_restored = new_state is not None and new_state.attributes.get(
            ATTR_RESTORED, False
        )
        if (
            old_state is not None
            and new_state is not None
            and old_restored == new_restored
        ):
            return

        _async_validate_configured_entities(hass, entry)

    @callback
    def _async_home_assistant_started(_event: Event[Any]) -> None:
        _async_validate_configured_entities(hass, entry)

    entry.async_on_unload(
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            _async_entity_registry_updated,
        )
    )
    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            _configured_entity_ids(entry),
            _async_state_changed,
        )
    )

    if hass.state is CoreState.running:
        _async_validate_configured_entities(hass, entry)
        return

    entry.async_on_unload(
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            _async_home_assistant_started,
        )
    )


@callback
def _async_validate_configured_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Create or clear the repair issue for invalid configured entities."""

    invalid_entity_ids = async_get_invalid_configured_entities(
        hass,
        _entry_config(entry),
    )
    issue_id = _issue_id(entry)
    if not invalid_entity_ids:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_INVALID_CONFIGURED_ENTITIES,
        translation_placeholders={
            "config_entry_title": entry.title,
            "invalid_entities": ", ".join(
                f"`{entity_id}`" for entity_id in invalid_entity_ids
            ),
        },
    )


def _entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return config entry data with options applied."""

    return {**entry.data, **entry.options}


def _configured_entity_ids(entry: ConfigEntry) -> tuple[str, ...]:
    """Return entity IDs referenced by a config entry."""

    return async_configured_entity_ids(_entry_config(entry))


def _issue_id(entry: ConfigEntry) -> str:
    """Return the stable repair issue ID for a config entry."""

    return f"{ISSUE_INVALID_CONFIGURED_ENTITIES}_{entry.entry_id}"
