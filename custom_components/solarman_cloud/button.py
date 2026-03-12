from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PLANT_ID, DOMAIN


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SolarmanValidatePlantButton(coordinator, entry)])


class SolarmanValidatePlantButton(ButtonEntity):
    def __init__(self, coordinator, entry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_validate_plant"
        self._attr_name = "Solarman Validar planta / Atualizar topologia"

    @property
    def device_info(self) -> DeviceInfo:
        plant_id = self.entry.data.get(CONF_PLANT_ID)
        plant = self.entry.data.get("topology", {}).get("plant", {})
        return DeviceInfo(
            identifiers={(DOMAIN, f"plant_{plant_id}")},
            name=plant.get("plantName") or f"Solarman Plant {plant_id}",
            manufacturer="Solarman",
            model="Plant",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_refresh_topology()
        await self.coordinator.async_request_refresh()
