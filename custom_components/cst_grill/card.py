"""Serve the bundled card, register it as a Lovelace resource, and manage the CST Grills dashboard."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import dashboard as ll_dashboard
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from .const import (
    CARD_URL, CARD_URL_VERSIONED, DASHBOARD_ICON, DASHBOARD_ID, DASHBOARD_TITLE,
    DASHBOARD_URL, DOMAIN, STATIC_BASE, VIEW_PREFIX,
)

_LOGGER = logging.getLogger(__name__)
_STATIC_DONE = f"{DOMAIN}_static_registered"
_EXTRA_JS = f"{DOMAIN}_extra_js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Static path + Lovelace resource (storage mode) or extra JS URL (YAML mode)."""
    if not hass.data.get(_STATIC_DONE):
        path = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_BASE, str(path), False)])
        hass.data[_STATIC_DONE] = True

    ll = hass.data.get(LOVELACE_DATA)
    resources = getattr(ll, "resources", None)
    if ll is not None and ll.resource_mode == "storage" and hasattr(resources, "async_create_item"):
        await resources._async_ensure_loaded()  # noqa: SLF001
        mine = [r for r in resources.async_items() if str(r.get("url", "")).startswith(CARD_URL)]
        if any(r["url"] == CARD_URL_VERSIONED for r in mine):
            return
        if mine:
            await resources.async_update_item(mine[0]["id"], {"res_type": "module", "url": CARD_URL_VERSIONED})
            for extra in mine[1:]:
                await resources.async_delete_item(extra["id"])
        else:
            await resources.async_create_item({"res_type": "module", "url": CARD_URL_VERSIONED})
        if any("cst-grill-card.js" in str(r.get("url")) and not str(r.get("url")).startswith(CARD_URL)
               for r in resources.async_items()):
            _LOGGER.warning("A manual cst-grill-card resource also exists; you can remove it (the integration serves %s)", CARD_URL)
        return

    if not hass.data.get(_EXTRA_JS):
        frontend.add_extra_js_url(hass, CARD_URL_VERSIONED)
        hass.data[_EXTRA_JS] = True


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


def _dash_item() -> dict[str, Any]:
    return {
        "id": DASHBOARD_ID, "url_path": DASHBOARD_URL, "title": DASHBOARD_TITLE, "icon": DASHBOARD_ICON,
        "show_in_sidebar": True, "require_admin": False, "mode": "storage",
    }


async def async_sync_dashboard(hass: HomeAssistant, grills: list[tuple[str, str]]) -> None:
    """Create/update the CST Grills dashboard with one view per grill. Views the user added are kept."""
    ll = hass.data[LOVELACE_DATA]
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
    managed = [
        {"title": name, "path": f"{VIEW_PREFIX}{dev_id[:8]}", "type": "masonry",
         "cards": [{"type": "custom:cst-grill-card", "device_id": dev_id}]}
        for dev_id, name in grills
    ]
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
