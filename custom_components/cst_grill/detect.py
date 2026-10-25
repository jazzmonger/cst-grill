"""Find ESPHome devices that look like CST 1-Pot grills (no entities are created)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


def _is_1pot(entity_ids: list[str]) -> bool:
    def has(domain: str, suffix: str) -> bool:
        return any(e.startswith(domain + ".") and e.endswith("_" + suffix) for e in entity_ids)

    return (
        has("number", "smoker_set_temperature")
        and has("select", "cook_mode")
        and has("sensor", "chamber_temperature")
    )


def find_grills(hass: HomeAssistant) -> dict[str, str]:
    """Return {device_id: name} for ESPHome devices that look like CST 1-Pot grills."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    by_dev: dict[str, list[str]] = {}
    for ent in ent_reg.entities.values():
        if ent.platform == "esphome" and ent.device_id:
            by_dev.setdefault(ent.device_id, []).append(ent.entity_id)
    out: dict[str, str] = {}
    for dev_id, ids in by_dev.items():
        dev = dev_reg.async_get(dev_id)
        if dev and _is_1pot(ids):
            out[dev_id] = dev.name_by_user or dev.name or dev_id
    return out
