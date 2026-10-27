"""Find ESPHome devices that look like CST 1-Pot grills (no entities are created)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


def _entity_has(domain: str, suffix: str, entity_ids: list[str]) -> bool:
    prefix = f"{domain}."
    tail = f"_{suffix}"
    return any(e.startswith(prefix) and e.endswith(tail) for e in entity_ids)


def _is_1pot(entity_ids: list[str]) -> bool:
    return (
        _entity_has("number", "smoker_set_temperature", entity_ids)
        and _entity_has("select", "cook_mode", entity_ids)
        and _entity_has("sensor", "chamber_temperature", entity_ids)
    )


def find_grills(hass: HomeAssistant) -> dict[str, str]:
    """Return {device_id: name} for ESPHome devices that look like CST 1-Pot grills."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    out: dict[str, str] = {}

    for entry in hass.config_entries.async_entries("esphome"):
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
            ids = [
                ent.entity_id
                for ent in er.async_entries_for_device(ent_reg, device.id)
            ]
            if not _is_1pot(ids):
                continue
            out[device.id] = device.name_by_user or device.name or device.id

    if out:
        return out

    # Legacy fallback (older HA / odd registry rows): group esphome-platform entities by device.
    by_dev: dict[str, list[str]] = {}
    for ent in ent_reg.entities.values():
        if ent.device_id and ent.platform == "esphome":
            by_dev.setdefault(ent.device_id, []).append(ent.entity_id)
    for dev_id, ids in by_dev.items():
        if not _is_1pot(ids):
            continue
        dev = dev_reg.async_get(dev_id)
        if dev:
            out[dev_id] = dev.name_by_user or dev.name or dev_id
    return out
