from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CHANNEL, DOMAIN
from .sensor import SolarmanBaseEntity


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for device_sn in coordinator.selected_device_sns:
        payload = coordinator.data.get("devices", {}).get(device_sn, {}) if coordinator.data else {}
        for channel in (payload.get("panels") or {}).keys():
            entities.append(SolarmanPanelStatusBinarySensor(coordinator, entry, device_sn, channel))
    async_add_entities(entities)


class SolarmanPanelStatusBinarySensor(SolarmanBaseEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, device_sn: str, channel: str) -> None:
        super().__init__(coordinator, entry, device_sn)
        self.channel = channel
        self._attr_unique_id = f"{entry.entry_id}_{device_sn}_panel_{channel}_status"
        self._attr_name = f"{self.coordinator.device_display_name(device_sn)} Placa {channel} ligada"

    @property
    def is_on(self):
        panel = ((self.coordinator.data or {}).get("devices", {}).get(self.device_sn, {}).get("panels") or {}).get(self.channel)
        return panel.status_on if panel else None

    @property
    def extra_state_attributes(self):
        attrs = self.common_attrs()
        attrs[ATTR_CHANNEL] = self.channel
        return attrs
