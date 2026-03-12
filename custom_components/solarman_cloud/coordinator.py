from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarmanAPI, SolarmanApiError, SolarmanAuthError
from .const import (
    ATTR_BUDGET_LIMIT,
    ATTR_ESTIMATED_PERCENT,
    ATTR_REQUESTS_PER_DAY,
    ATTR_REQUESTS_PER_YEAR,
    ATTR_SAFE_LIMIT,
    ATTR_WINDOW_MINUTES,
    CONF_DEFAULT_PANEL_CAPACITY_W,
    CONF_DEVICE_TYPE,
    CONF_END_TIME,
    CONF_PLANT_ID,
    CONF_REQUEST_LIMIT,
    CONF_SAFE_PERCENT,
    CONF_SELECTED_DEVICE_SNS,
    CONF_START_TIME,
    CONF_TOPOLOGY,
    CONF_UPDATE_INTERVAL_MINUTES,
)
from .helpers import RequestBudget, infer_device_name, infer_device_sn, parse_hhmm
from .parser import flatten_current_data, parse_canonical_metrics, parse_panel_metrics

_LOGGER = logging.getLogger(__name__)


class SolarmanDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SolarmanAPI) -> None:
        self.entry = entry
        self.api = api
        self.topology = entry.data.get(CONF_TOPOLOGY, {})
        self.selected_device_sns = list(entry.options.get(CONF_SELECTED_DEVICE_SNS, entry.data.get(CONF_SELECTED_DEVICE_SNS, [])))
        self.device_type = entry.options.get(CONF_DEVICE_TYPE, entry.data.get(CONF_DEVICE_TYPE, "MICRO_INVERTER"))
        self.request_budget = self._build_budget()
        interval = timedelta(minutes=entry.options.get(CONF_UPDATE_INTERVAL_MINUTES, entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, 6)))
        super().__init__(hass, _LOGGER, name="Solarman Cloud", update_interval=interval)

    def _build_budget(self) -> RequestBudget:
        return RequestBudget(
            request_limit=int(self.entry.options.get(CONF_REQUEST_LIMIT, self.entry.data.get(CONF_REQUEST_LIMIT, 200000))),
            safe_percent=int(self.entry.options.get(CONF_SAFE_PERCENT, self.entry.data.get(CONF_SAFE_PERCENT, 90))),
            device_count=len(self.entry.options.get(CONF_SELECTED_DEVICE_SNS, self.entry.data.get(CONF_SELECTED_DEVICE_SNS, []))),
            update_interval_minutes=int(self.entry.options.get(CONF_UPDATE_INTERVAL_MINUTES, self.entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, 6))),
            start_time=self.entry.options.get(CONF_START_TIME, self.entry.data.get(CONF_START_TIME, "05:30")),
            end_time=self.entry.options.get(CONF_END_TIME, self.entry.data.get(CONF_END_TIME, "19:30")),
        )

    def _inside_window(self) -> bool:
        start = self.entry.options.get(CONF_START_TIME, self.entry.data.get(CONF_START_TIME, "05:30"))
        end = self.entry.options.get(CONF_END_TIME, self.entry.data.get(CONF_END_TIME, "19:30"))
        sh, sm = parse_hhmm(start)
        eh, em = parse_hhmm(end)
        now = datetime.now().time()
        start_t = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        end_t = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        current = now.replace(second=0, microsecond=0)
        if start_t <= end_t:
            return start_t <= current <= end_t
        return current >= start_t or current <= end_t

    async def async_refresh_topology(self) -> dict[str, Any]:
        plant_id = self.entry.data.get(CONF_PLANT_ID)
        plant = await self.api.get_plant_basic(plant_id)
        devices = await self.api.list_plant_devices(plant_id)
        filtered = [d for d in devices if infer_device_sn(d) in set(self.selected_device_sns)] or devices
        topology = {"plant": plant, "devices": filtered}
        self.topology = topology
        new_data = {**self.entry.data, CONF_TOPOLOGY: topology, CONF_SELECTED_DEVICE_SNS: [infer_device_sn(d) for d in filtered]}
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)
        return topology

    async def _async_update_data(self) -> dict[str, Any]:
        if not self._inside_window():
            return self.data if self.data else {"devices": {}, "meta": self._meta()}

        devices_payload: dict[str, Any] = {}
        try:
            for device_sn in self.selected_device_sns:
                payload = await self.api.get_device_current_data(device_sn, self.device_type)
                flat = flatten_current_data(payload)
                canonical = parse_canonical_metrics(flat)
                panels = parse_panel_metrics(flat, int(self.entry.options.get(CONF_DEFAULT_PANEL_CAPACITY_W, self.entry.data.get(CONF_DEFAULT_PANEL_CAPACITY_W, 550))))
                devices_payload[device_sn] = {
                    "raw": payload,
                    "flat": flat,
                    "canonical": canonical,
                    "panels": panels,
                }
        except SolarmanAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except SolarmanApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        return {"devices": devices_payload, "meta": self._meta()}

    def _meta(self) -> dict[str, Any]:
        budget = self._build_budget()
        return {
            ATTR_REQUESTS_PER_DAY: budget.requests_per_day,
            ATTR_REQUESTS_PER_YEAR: budget.requests_per_year,
            ATTR_BUDGET_LIMIT: budget.request_limit,
            ATTR_SAFE_LIMIT: budget.safe_limit,
            ATTR_ESTIMATED_PERCENT: budget.estimated_percent,
            ATTR_WINDOW_MINUTES: budget.window_minutes,
        }

    def get_device_topology(self, device_sn: str) -> dict[str, Any]:
        for device in self.topology.get("devices", []):
            if infer_device_sn(device) == device_sn:
                return device
        return {"deviceSn": device_sn, "name": device_sn}

    def device_display_name(self, device_sn: str) -> str:
        return infer_device_name(self.get_device_topology(device_sn))
