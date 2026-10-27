"""Serve the bundled card, register it as a Lovelace resource, and manage the CST Grills dashboard."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import dashboard as ll_dashboard
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant, callback

from .const import (
    CARD_URL, CARD_URL_VERSIONED, DASHBOARD_ICON, DASHBOARD_ID, DASHBOARD_TITLE,
    DASHBOARD_URL, DOMAIN, STATIC_BASE, VIEW_PREFIX,
)

_LOGGER = logging.getLogger(__name__)
_STATIC_DONE = f"{DOMAIN}_static_registered"
_EXTRA_JS = f"{DOMAIN}_extra_js"
_RETRY_TASK = f"{DOMAIN}_card_register_retries"
_RETRY_DELAYS_S = (0, 2, 5, 15, 60)


async def _register_static(hass: HomeAssistant) -> None:
    if hass.data.get(_STATIC_DONE):
        return
    path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_BASE, str(path), False)])
    hass.data[_STATIC_DONE] = True


def _storage_resource_ok(hass: HomeAssistant) -> bool:
    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        return False
    if ll.resource_mode != "storage":
        return True
    resources = getattr(ll, "resources", None)
    if resources is None:
        return False
    return any(str(r.get("url", "")).startswith(CARD_URL) for r in resources.async_items())


async def _register_lovelace_resource(hass: HomeAssistant) -> bool:
    """Register card JS in Lovelace resources (storage) and via frontend extra_js (always)."""
    stored = False
    ll = hass.data.get(LOVELACE_DATA)
    resources = getattr(ll, "resources", None) if ll is not None else None
    if (
        ll is not None
        and ll.resource_mode == "storage"
        and resources is not None
        and hasattr(resources, "async_create_item")
    ):
        await resources._async_ensure_loaded()  # noqa: SLF001
        mine = [r for r in resources.async_items() if str(r.get("url", "")).startswith(CARD_URL)]
        if any(r["url"] == CARD_URL_VERSIONED for r in mine):
            stored = True
        elif mine:
            await resources.async_update_item(mine[0]["id"], {"res_type": "module", "url": CARD_URL_VERSIONED})
            for extra in mine[1:]:
                await resources.async_delete_item(extra["id"])
            stored = True
        else:
            await resources.async_create_item({"res_type": "module", "url": CARD_URL_VERSIONED})
            stored = True
            _LOGGER.info("CST Grill: added Lovelace resource %s (no manual step needed)", CARD_URL_VERSIONED)
        if any(
            "cst-grill-card.js" in str(r.get("url"))
            and not str(r.get("url")).startswith(CARD_URL)
            for r in resources.async_items()
        ):
            _LOGGER.warning(
                "Duplicate cst-grill-card resource in Lovelace; remove /local copy (integration serves %s)",
                CARD_URL,
            )

    if not hass.data.get(_EXTRA_JS):
        frontend.add_extra_js_url(hass, CARD_URL_VERSIONED)
        hass.data[_EXTRA_JS] = True

    if ll is not None and ll.resource_mode == "storage":
        return stored
    return bool(hass.data.get(_EXTRA_JS))


def _card_ready(hass: HomeAssistant) -> bool:
    if not hass.data.get(_STATIC_DONE) and not hass.data.get(_EXTRA_JS):
        return False
    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        return False
    if ll.resource_mode == "storage":
        return _storage_resource_ok(hass)
    return bool(hass.data.get(_EXTRA_JS))


async def async_register_card(hass: HomeAssistant) -> bool:
    """Static path + Lovelace resource. Returns True when registration is complete for this HA mode."""
    await _register_static(hass)
    return await _register_lovelace_resource(hass)


async def _register_with_retries(hass: HomeAssistant) -> None:
    """Keep trying until Lovelace exists and the storage resource row is created."""
    for delay in _RETRY_DELAYS_S:
        if delay:
            await asyncio.sleep(delay)
        ok = await async_register_card(hass)
        if _card_ready(hass):
            _LOGGER.debug("CST Grill card JS ready (last_register_ok=%s)", ok)
            return
    _LOGGER.error(
        "CST Grill card JS not registered after retries; reload integration or restart HA"
    )


def async_schedule_card_register(hass: HomeAssistant) -> None:
    """Start background registration (safe to call from async_setup and setup_entry)."""
    existing = hass.data.get(_RETRY_TASK)
    if existing and not existing.done():
        return
    hass.data[_RETRY_TASK] = hass.async_create_task(_register_with_retries(hass))


async def async_unregister_card(hass: HomeAssistant) -> None:
    """Remove the integration's resource (only called when the last entry is removed)."""
    ll = hass.data.get(LOVELACE_DATA)
    resources = getattr(ll, "resources", None)
    if ll is not None and ll.resource_mode == "storage" and hasattr(resources, "async_delete_item"):
        await resources._async_ensure_loaded()  # noqa: SLF001
        for r in list(resources.async_items()):
            if str(r.get("url", "")).startswith(CARD_URL):
                await resources.async_delete_item(r["id"])
    if hass.data.pop(_EXTRA_JS, False):
        frontend.remove_extra_js_url(hass, CARD_URL_VERSIONED)
    task = hass.data.pop(_RETRY_TASK, None)
    if task and not task.done():
        task.cancel()


def _dash_item() -> dict[str, Any]:
    return {
        "id": DASHBOARD_ID, "url_path": DASHBOARD_URL, "title": DASHBOARD_TITLE, "icon": DASHBOARD_ICON,
        "show_in_sidebar": True, "require_admin": False, "mode": "storage",
    }


def _grill_view(dev_id: str, name: str) -> dict[str, Any]:
    return {
        "title": name,
        "path": f"{VIEW_PREFIX}{dev_id[:8]}",
        "type": "panel",
        "cards": [{"type": "custom:cst-grill-card", "device_id": dev_id}],
    }


async def async_sync_dashboard(hass: HomeAssistant, grills: list[tuple[str, str]]) -> None:
    """Create/update the CST Grills dashboard with one view per grill. Views the user added are kept."""
    async_schedule_card_register(hass)

    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        _LOGGER.debug("Lovelace not ready; defer CST Grills dashboard sync")

        @callback
        def _on_lovelace(_event: Any) -> None:
            hass.async_create_task(async_sync_dashboard(hass, grills))

        hass.bus.async_listen_once("lovelace_loaded", _on_lovelace)
        return

    if not _card_ready(hass):
        await async_register_card(hass)
    if not _card_ready(hass):
        _LOGGER.debug("CST Grill card not ready yet; dashboard sync will retry with registration")

    dash = ll.dashboards.get(DASHBOARD_URL)
    if dash is None:
        dash = ll_dashboard.LovelaceStorage(hass, _dash_item())
        ll.dashboards[DASHBOARD_URL] = dash
    if not grills:
        return await async_remove_dashboard(hass, delete=True)
    item = _dash_item()
    frontend.async_register_built_in_panel(
        hass, "lovelace", frontend_url_path=DASHBOARD_URL, require_admin=False, show_in_sidebar=True,
        sidebar_title=DASHBOARD_TITLE, sidebar_icon=item["icon"], config={"mode": "storage"},
        update=DASHBOARD_URL in hass.data.get("frontend_panels", {}),
    )
    try:
        cfg = await dash.async_load(False)
    except Exception:  # noqa: BLE001 - ConfigNotFound on first run
        cfg = {"title": DASHBOARD_TITLE, "views": []}
    others = [v for v in cfg.get("views", []) if not str(v.get("path", "")).startswith(VIEW_PREFIX)]
    managed = [_grill_view(dev_id, name) for dev_id, name in grills]
    new = {**cfg, "title": DASHBOARD_TITLE, "views": managed + others}
    if new != cfg:
        await dash.async_save(new)


async def async_remove_dashboard(hass: HomeAssistant, delete: bool) -> None:
    """Unregister the panel; delete its stored config when the integration is removed."""
    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        return
    if DASHBOARD_URL in hass.data.get("frontend_panels", {}):
        frontend.async_remove_panel(hass, DASHBOARD_URL)
    dash = ll.dashboards.pop(DASHBOARD_URL, None)
    if delete:
        if dash is None:
            dash = ll_dashboard.LovelaceStorage(hass, _dash_item())
        await dash.async_delete()
