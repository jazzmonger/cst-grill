"""Config flow: pick a CST grill (an ESPHome device) to add the dashboard for."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import CONF_CREATE_DASHBOARD, CONF_DEVICE_ID, DOMAIN
from .detect import find_grills


class CstGrillConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        grills = find_grills(self.hass)
        configured = {e.unique_id for e in self._async_current_entries()}
        choices = {d: f"{n} ({k})" for d, (n, k) in grills.items() if d not in configured}
        if user_input is not None:
            dev = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(dev)
            self._abort_if_unique_id_configured()
            name, kind = grills[dev]
            return self.async_create_entry(
                title=name, data={CONF_DEVICE_ID: dev, "kind": kind},
                options={CONF_CREATE_DASHBOARD: user_input.get(CONF_CREATE_DASHBOARD, True)},
            )
        if not choices:
            return self.async_abort(reason="no_grills")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(choices),
                vol.Optional(CONF_CREATE_DASHBOARD, default=True): bool,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CstGrillOptionsFlow()


class CstGrillOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        cur = self.config_entry.options.get(CONF_CREATE_DASHBOARD, True)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional(CONF_CREATE_DASHBOARD, default=cur): bool}),
        )
