from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import SolarmanApiError, SolarmanCloudApi
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_BASE_URL,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_INCLUDE_PLANT_SENSORS,
    CONF_LANGUAGE,
    CONF_LOGIN_TYPE,
    CONF_ORG_ID,
    CONF_PASSWORD,
    CONF_PASSWORD_ALREADY_SHA256,
    CONF_PLANT_ID,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_INCLUDE_PLANT_SENSORS,
    DEFAULT_LANGUAGE,
    DEFAULT_POLL_INTERVAL,
    DEVICE_TYPES,
    DOMAIN,
    LOGIN_EMAIL,
    LOGIN_TYPES,
)

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
            vol.Required(CONF_APP_ID, default=defaults.get(CONF_APP_ID, "")): str,
            vol.Required(CONF_APP_SECRET, default=defaults.get(CONF_APP_SECRET, "")): str,
            vol.Required(CONF_LOGIN_TYPE, default=defaults.get(CONF_LOGIN_TYPE, LOGIN_EMAIL)): vol.In(LOGIN_TYPES),
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
            vol.Optional(CONF_ORG_ID, default=defaults.get(CONF_ORG_ID, "")): str,
            vol.Optional(CONF_PLANT_ID, default=defaults.get(CONF_PLANT_ID, "")): str,
            vol.Optional(CONF_DEVICE_SN, default=defaults.get(CONF_DEVICE_SN, "")): str,
            vol.Required(CONF_DEVICE_TYPE, default=defaults.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)): vol.In(DEVICE_TYPES),
            vol.Required(CONF_LANGUAGE, default=defaults.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)): str,
            vol.Required(CONF_POLL_INTERVAL, default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)): int,
            vol.Required(
                CONF_PASSWORD_ALREADY_SHA256,
                default=defaults.get(CONF_PASSWORD_ALREADY_SHA256, False),
            ): bool,
            vol.Required(
                CONF_INCLUDE_PLANT_SENSORS,
                default=defaults.get(CONF_INCLUDE_PLANT_SENSORS, DEFAULT_INCLUDE_PLANT_SENSORS),
            ): bool,
        }
    )


def _options_schema(config: dict[str, Any], options: dict[str, Any]) -> vol.Schema:
    merged = {**config, **options}
    return vol.Schema(
        {
            vol.Required(CONF_POLL_INTERVAL, default=merged.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)): int,
            vol.Required(
                CONF_INCLUDE_PLANT_SENSORS,
                default=merged.get(CONF_INCLUDE_PLANT_SENSORS, DEFAULT_INCLUDE_PLANT_SENSORS),
            ): bool,
            vol.Required(CONF_DEVICE_TYPE, default=merged.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)): vol.In(DEVICE_TYPES),
            vol.Optional(CONF_PLANT_ID, default=merged.get(CONF_PLANT_ID, "")): str,
            vol.Optional(CONF_DEVICE_SN, default=merged.get(CONF_DEVICE_SN, "")): str,
        }
    )


async def _validate_input(hass, data: dict[str, Any]) -> dict[str, Any]:
    session = async_create_clientsession(hass)
    api = SolarmanCloudApi(session, data)
    result = await api.async_validate()
    discovered = result["discovered"]
    plant = discovered["plant"]
    selected_device = discovered["selected_device"]
    title = f"{plant.get('name', 'Solarman')} - {selected_device.get('deviceSn', 'device')}"
    return {
        "title": title,
        "plant_id": api.selected_plant_id,
        "device_sn": api.selected_device_sn,
    }


class SolarmanCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except (SolarmanApiError, Exception) as exc:
                _LOGGER.exception("Erro de validação Solarman: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                unique_id = f"{user_input[CONF_APP_ID]}::{info['device_sn']}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_user_schema(user_input), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SolarmanCloudOptionsFlow(config_entry)


class SolarmanCloudOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry.data, self.config_entry.options),
            errors={},
        )
