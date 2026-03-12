from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_SN,
    ATTR_PLANT_ID,
    ATTR_RAW_KEY,
    ATTR_SOURCE,
    CONF_INCLUDE_PLANT_SENSORS,
    DOMAIN,
)
from .coordinator import SolarmanCloudCoordinator

UNIT_MAP = {
    "W": UnitOfPower.WATT,
    "kW": "kW",
    "V": UnitOfElectricPotential.VOLT,
    "A": UnitOfElectricCurrent.AMPERE,
    "°C": UnitOfTemperature.CELSIUS,
    "C": UnitOfTemperature.CELSIUS,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "%": "%",
    "Hz": "Hz",
}

KEY_HINTS = {
    "generationpower": {"device_class": "power", "state_class": SensorStateClass.MEASUREMENT},
    "pac": {"device_class": "power", "state_class": SensorStateClass.MEASUREMENT},
    "etoday": {"state_class": SensorStateClass.TOTAL_INCREASING},
    "generationtoday": {"state_class": SensorStateClass.TOTAL_INCREASING},
    "etotal": {"state_class": SensorStateClass.TOTAL_INCREASING},
    "generationtotal": {"state_class": SensorStateClass.TOTAL_INCREASING},
    "temperature": {"device_class": "temperature", "state_class": SensorStateClass.MEASUREMENT},
}


@dataclass
class DynamicSensorDescription(SensorEntityDescription):
    raw_key: str = ""
    source: str = "device"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SolarmanCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    selected = coordinator.data.get("selected", {})
    device = coordinator.data.get("device", {})
    plant = coordinator.data.get("plant", {})

    for item in device.get("dataList", []):
        description = _description_from_item(item, source="device")
        entities.append(SolarmanDynamicSensor(coordinator, description, selected))

    if entry.options.get(CONF_INCLUDE_PLANT_SENSORS, entry.data.get(CONF_INCLUDE_PLANT_SENSORS, True)):
        for key, value in plant.items():
            if isinstance(value, (str, int, float)):
                description = _description_from_scalar(key, source="plant")
                entities.append(SolarmanScalarSensor(coordinator, description, selected))

    async_add_entities(entities)


def _normalize(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


def _friendly_name(raw_key: str) -> str:
    return raw_key.replace("_", " ").replace("-", " ").title()


def _parse_number(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return value
    txt = value.strip().replace(",", ".")
    try:
        if "." in txt:
            return float(txt)
        return int(txt)
    except ValueError:
        return value


def _description_from_item(item: dict[str, Any], *, source: str) -> DynamicSensorDescription:
    raw_key = item.get("key") or item.get("name") or "unknown"
    norm = _normalize(raw_key)
    unit = item.get("unit")
    hints = KEY_HINTS.get(norm, {})
    return DynamicSensorDescription(
        key=f"{source}_{raw_key}",
        name=item.get("name") or _friendly_name(raw_key),
        native_unit_of_measurement=UNIT_MAP.get(unit, unit),
        icon="mdi:solar-power",
        device_class=hints.get("device_class"),
        state_class=hints.get("state_class"),
        raw_key=raw_key,
        source=source,
    )


def _description_from_scalar(key: str, *, source: str) -> DynamicSensorDescription:
    raw_key = key
    norm = _normalize(raw_key)
    hints = KEY_HINTS.get(norm, {})
    return DynamicSensorDescription(
        key=f"{source}_{raw_key}",
        name=f"Plant {_friendly_name(raw_key)}",
        icon="mdi:solar-panel",
        device_class=hints.get("device_class"),
        state_class=hints.get("state_class"),
        raw_key=raw_key,
        source=source,
    )


class SolarmanBaseSensor(CoordinatorEntity[SolarmanCloudCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarmanCloudCoordinator, description: DynamicSensorDescription, selected: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._selected = selected
        self._attr_unique_id = f"{selected.get('device_sn','device')}::{description.source}::{description.raw_key}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._selected.get("device_sn", "unknown"))},
            "manufacturer": "Solarman",
            "name": f"Solarman {self._selected.get('device_sn', 'Device')}",
            "model": self._selected.get("device_type", "Cloud API"),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_DEVICE_SN: self._selected.get("device_sn"),
            ATTR_DEVICE_ID: self._selected.get("device_id"),
            ATTR_PLANT_ID: self._selected.get("plant_id"),
            ATTR_SOURCE: self.entity_description.source,
            ATTR_RAW_KEY: self.entity_description.raw_key,
        }


class SolarmanDynamicSensor(SolarmanBaseSensor):
    @property
    def native_value(self) -> Any:
        data_list = self.coordinator.data.get("device", {}).get("dataList", [])
        for item in data_list:
            if (item.get("key") or item.get("name")) == self.entity_description.raw_key:
                return _parse_number(item.get("value"))
        return None


class SolarmanScalarSensor(SolarmanBaseSensor):
    @property
    def native_value(self) -> Any:
        value = self.coordinator.data.get("plant", {}).get(self.entity_description.raw_key)
        return _parse_number(value)
