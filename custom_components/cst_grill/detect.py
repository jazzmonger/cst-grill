"""Find ESPHome devices that look like CST grills (no entities are created)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er


def _kind(entity_ids: list[str]) -> str | None:
    def has(domain: str, suffix: str) -> bool:
        return any(e.startswith(domain + ".") and e.endswith("_" + suffix) for e in entity_ids)

    if not has("number", "smoker_set_temperature"):
        return None
    if has("select", "cook_mode") and has("sensor", "chamber_temperature"):
        return "1-Pot"
    if has("sensor", "rtd_temperature"):
        return "5-Pot"
    return None


def find_grills(hass: HomeAssistant) -> dict[str, tuple[str, str]]:
    """Return {device_id: (name, kind)} for ESPHome devices that look like CST grills."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    by_dev: dict[str, list[str]] = {}
    for ent in ent_reg.entities.values():
        if ent.platform == "esphome" and ent.device_id:
            by_dev.setdefault(ent.device_id, []).append(ent.entity_id)
    out: dict[str, tuple[str, str]] = {}
    for dev_id, ids in by_dev.items():
        kind = _kind(ids)
        dev = dev_reg.async_get(dev_id)
        if kind and dev:
            out[dev_id] = (dev.name_by_user or dev.name or dev_id, kind)
    return out
