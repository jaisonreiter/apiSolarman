from __future__ import annotations

from typing import Any

import voluptuous as vol
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectSelectorOptionDict,
    TextSelector,
    TextSelectorConfig,
)

from .api import SolarmanAPI, SolarmanApiError
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_BASE_URL,
    CONF_DEFAULT_PANEL_CAPACITY_W,
    CONF_DEVICE_TYPE,
    CONF_END_TIME,
    CONF_GITHUB_REPO,
    CONF_HASH_PASSWORD,
    CONF_INCLUDE_PLANT_SENSORS,
    CONF_LOGIN_TYPE,
    CONF_ORG_ID,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_REQUEST_LIMIT,
    CONF_SAFE_PERCENT,
    CONF_SELECTED_DEVICE_SNS,
    CONF_START_TIME,
    CONF_TOPOLOGY,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_USERNAME,
    DEFAULT_BASE_URL,
    DEFAULT_DEFAULT_PANEL_CAPACITY_W,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_END_TIME,
    DEFAULT_GITHUB_REPO,
    DEFAULT_LOGIN_TYPE,
    DEFAULT_REQUEST_LIMIT,
    DEFAULT_SAFE_PERCENT,
    DEFAULT_START_TIME,
    DEFAULT_UPDATE_MINUTES,
    DEVICE_TYPES,
    DOMAIN,
    LOGIN_TYPES,
)
from .helpers import RequestBudget, infer_device_name, infer_device_sn


class SolarmanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []
        self._plants: list[dict[str, Any]] = []
        self._topology: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._user_input = user_input
            try:
                session = async_create_clientsession(self.hass)
                api = SolarmanAPI(
                    session,
                    user_input[CONF_BASE_URL],
                    user_input[CONF_APP_ID],
                    user_input[CONF_APP_SECRET],
                    user_input[CONF_LOGIN_TYPE],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input.get(CONF_ORG_ID),
                    hash_password=user_input.get(CONF_HASH_PASSWORD, False),
                )
                await api.authenticate()
                self._plants = await api.list_plants()
            except SolarmanApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return await self.async_step_select_plant()

        schema = vol.Schema({
            vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(TextSelectorConfig(type="url")),
            vol.Required(CONF_APP_ID): str,
            vol.Required(CONF_APP_SECRET): str,
            vol.Required(CONF_LOGIN_TYPE, default=DEFAULT_LOGIN_TYPE): SelectSelector(SelectSelectorConfig(options=LOGIN_TYPES, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_ORG_ID, default=""): str,
            vol.Optional(CONF_HASH_PASSWORD, default=False): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_plant(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._user_input.update(user_input)
            plant_id = user_input[CONF_PLANT_ID]
            session = async_create_clientsession(self.hass)
            api = SolarmanAPI(
                session,
                self._user_input[CONF_BASE_URL],
                self._user_input[CONF_APP_ID],
                self._user_input[CONF_APP_SECRET],
                self._user_input[CONF_LOGIN_TYPE],
                self._user_input[CONF_USERNAME],
                self._user_input[CONF_PASSWORD],
                self._user_input.get(CONF_ORG_ID),
                hash_password=self._user_input.get(CONF_HASH_PASSWORD, False),
            )
            try:
                await api.authenticate()
                plant = await api.get_plant_basic(plant_id)
                self._devices = await api.list_plant_devices(plant_id)
                self._topology = {"plant": plant, "devices": self._devices}
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_runtime()

        options = []
        for plant in self._plants:
            pid = plant.get("plantId") or plant.get("id") or plant.get("stationId")
            name = plant.get("plantName") or plant.get("name") or str(pid)
            options.append(SelectSelectorOptionDict(value=str(pid), label=f"{name} ({pid})"))
        schema = vol.Schema({
            vol.Required(CONF_PLANT_ID): SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN))
        })
        return self.async_show_form(step_id="select_plant", data_schema=schema, errors=errors)

    async def async_step_runtime(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        device_options = [SelectSelectorOptionDict(value=infer_device_sn(d), label=f"{infer_device_name(d)} ({infer_device_sn(d)})") for d in self._devices]

        if user_input is not None:
            selected = user_input[CONF_SELECTED_DEVICE_SNS]
            budget = RequestBudget(
                request_limit=int(user_input[CONF_REQUEST_LIMIT]),
                safe_percent=int(user_input[CONF_SAFE_PERCENT]),
                device_count=len(selected),
                update_interval_minutes=int(user_input[CONF_UPDATE_INTERVAL_MINUTES]),
                start_time=user_input[CONF_START_TIME],
                end_time=user_input[CONF_END_TIME],
            )
            if budget.requests_per_year > budget.safe_limit:
                errors[CONF_UPDATE_INTERVAL_MINUTES] = "interval_too_low"
                errors["base"] = "request_budget_exceeded"
            else:
                data = {**self._user_input, **user_input, CONF_TOPOLOGY: self._topology}
                title = self._topology.get("plant", {}).get("plantName") or "Solarman"
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema({
            vol.Required(CONF_SELECTED_DEVICE_SNS, default=[infer_device_sn(d) for d in self._devices]): SelectSelector(SelectSelectorConfig(options=device_options, multiple=True, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_DEVICE_TYPE, default=DEFAULT_DEVICE_TYPE): SelectSelector(SelectSelectorConfig(options=DEVICE_TYPES, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_UPDATE_INTERVAL_MINUTES, default=DEFAULT_UPDATE_MINUTES): NumberSelector(NumberSelectorConfig(min=1, max=240, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_START_TIME, default=DEFAULT_START_TIME): str,
            vol.Required(CONF_END_TIME, default=DEFAULT_END_TIME): str,
            vol.Required(CONF_REQUEST_LIMIT, default=DEFAULT_REQUEST_LIMIT): NumberSelector(NumberSelectorConfig(min=1, max=10000000, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_SAFE_PERCENT, default=DEFAULT_SAFE_PERCENT): NumberSelector(NumberSelectorConfig(min=1, max=100, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_DEFAULT_PANEL_CAPACITY_W, default=DEFAULT_DEFAULT_PANEL_CAPACITY_W): NumberSelector(NumberSelectorConfig(min=1, max=2000, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_INCLUDE_PLANT_SENSORS, default=False): bool,
            vol.Optional(CONF_GITHUB_REPO, default=DEFAULT_GITHUB_REPO): str,
        })
        return self.async_show_form(step_id="runtime", data_schema=schema, errors=errors, description_placeholders={"default_limit": str(DEFAULT_REQUEST_LIMIT)})

    @staticmethod
    def async_get_options_flow(config_entry):
        return SolarmanOptionsFlow(config_entry)


class SolarmanOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        data = self.config_entry.data
        options = dict(self.config_entry.options)
        selected = options.get(CONF_SELECTED_DEVICE_SNS, data.get(CONF_SELECTED_DEVICE_SNS, []))
        if user_input is not None:
            budget = RequestBudget(
                request_limit=int(user_input[CONF_REQUEST_LIMIT]),
                safe_percent=int(user_input[CONF_SAFE_PERCENT]),
                device_count=len(user_input[CONF_SELECTED_DEVICE_SNS]),
                update_interval_minutes=int(user_input[CONF_UPDATE_INTERVAL_MINUTES]),
                start_time=user_input[CONF_START_TIME],
                end_time=user_input[CONF_END_TIME],
            )
            if budget.requests_per_year > budget.safe_limit:
                errors[CONF_UPDATE_INTERVAL_MINUTES] = "interval_too_low"
                errors["base"] = "request_budget_exceeded"
            else:
                return self.async_create_entry(title="", data=user_input)

        device_options = [SelectSelectorOptionDict(value=infer_device_sn(d), label=f"{infer_device_name(d)} ({infer_device_sn(d)})") for d in data.get(CONF_TOPOLOGY, {}).get("devices", [])]
        schema = vol.Schema({
            vol.Required(CONF_SELECTED_DEVICE_SNS, default=selected): SelectSelector(SelectSelectorConfig(options=device_options, multiple=True, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_DEVICE_TYPE, default=options.get(CONF_DEVICE_TYPE, data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE))): SelectSelector(SelectSelectorConfig(options=DEVICE_TYPES, mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_UPDATE_INTERVAL_MINUTES, default=options.get(CONF_UPDATE_INTERVAL_MINUTES, data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_MINUTES))): NumberSelector(NumberSelectorConfig(min=1, max=240, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_START_TIME, default=options.get(CONF_START_TIME, data.get(CONF_START_TIME, DEFAULT_START_TIME))): str,
            vol.Required(CONF_END_TIME, default=options.get(CONF_END_TIME, data.get(CONF_END_TIME, DEFAULT_END_TIME))): str,
            vol.Required(CONF_REQUEST_LIMIT, default=options.get(CONF_REQUEST_LIMIT, data.get(CONF_REQUEST_LIMIT, DEFAULT_REQUEST_LIMIT))): NumberSelector(NumberSelectorConfig(min=1, max=10000000, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_SAFE_PERCENT, default=options.get(CONF_SAFE_PERCENT, data.get(CONF_SAFE_PERCENT, DEFAULT_SAFE_PERCENT))): NumberSelector(NumberSelectorConfig(min=1, max=100, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_DEFAULT_PANEL_CAPACITY_W, default=options.get(CONF_DEFAULT_PANEL_CAPACITY_W, data.get(CONF_DEFAULT_PANEL_CAPACITY_W, DEFAULT_DEFAULT_PANEL_CAPACITY_W))): NumberSelector(NumberSelectorConfig(min=1, max=2000, mode=NumberSelectorMode.BOX)),
            vol.Optional(CONF_INCLUDE_PLANT_SENSORS, default=options.get(CONF_INCLUDE_PLANT_SENSORS, data.get(CONF_INCLUDE_PLANT_SENSORS, False))): bool,
            vol.Optional(CONF_GITHUB_REPO, default=options.get(CONF_GITHUB_REPO, data.get(CONF_GITHUB_REPO, DEFAULT_GITHUB_REPO))): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors, description_placeholders={"default_limit": str(DEFAULT_REQUEST_LIMIT)})
