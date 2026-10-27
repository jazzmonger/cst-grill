"""CST Grill: dashboard + card for Chain Smoker grills that are already in HA via ESPHome.

This integration creates no entities. It serves the bundled cst-grill-card, registers it as a
Lovelace resource and (optionally) maintains a "CST Grills" dashboard with one view per grill.
"""
from __future__ import annotations

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import CONF_CREATE_DASHBOARD, CONF_DEVICE_ID, DOMAIN
from .card import (
    async_remove_dashboard,
    async_schedule_card_register,
    async_sync_dashboard,
    async_unregister_card,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _grills_for_dashboard(hass: HomeAssistant, exclude: str | None = None) -> list[tuple[str, str]]:
    dev_reg = dr.async_get(hass)
    out = []
    for e in hass.config_entries.async_entries(DOMAIN):
        if e.entry_id == exclude or not e.options.get(CONF_CREATE_DASHBOARD, True):
            continue
        dev = dev_reg.async_get(e.data[CONF_DEVICE_ID])
        out.append((e.data[CONF_DEVICE_ID], (dev.name_by_user or dev.name) if dev else e.title))
    return out


async def _sync_all(hass: HomeAssistant) -> None:
    await async_sync_dashboard(hass, _grills_for_dashboard(hass))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async_schedule_card_register(hass)
    if LOVELACE_DATA in hass.data:
        await _sync_all(hass)
    else:
        @callback
        def _on_lovelace(_event) -> None:
            hass.async_create_task(_sync_all(hass))

        hass.bus.async_listen_once("lovelace_loaded", _on_lovelace)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await _sync_all(hass)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not _grills_for_dashboard(hass, exclude=entry.entry_id):
        await async_remove_dashboard(hass, delete=False)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    others = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
    if not others:
        await async_remove_dashboard(hass, delete=True)
        await async_unregister_card(hass)
    else:
        await async_sync_dashboard(hass, _grills_for_dashboard(hass, exclude=entry.entry_id))
