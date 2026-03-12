from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CHANNEL,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_SN,
    ATTR_PLANT_ID,
    ATTR_RAW_KEY,
    ATTR_SOURCE,
    CONF_PLANT_ID,
    DOMAIN,
)
from .coordinator import SolarmanDataCoordinator
from .helpers import slugify

CANONICAL_SENSORS = {
    "generation_power": ("Potência de geração", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, "W"),
    "energy_today": ("Energia hoje", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "kWh"),
    "energy_total": ("Energia total", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, "kWh"),
    "inverter_temperature": ("Temperatura do inversor", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, "°C"),
    "grid_voltage": ("Tensão da rede", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, "V"),
    "grid_current": ("Corrente da rede", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, "A"),
    "grid_frequency": ("Frequência da rede", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, "Hz"),
    "power_factor": ("Fator de potência", None, SensorStateClass.MEASUREMENT, "%"),
    "status": ("Status", None, None, None),
}


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SolarmanDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [SolarmanBudgetSensor(coordinator, entry)]
    include_plant = entry.options.get("include_plant_sensors", entry.data.get("include_plant_sensors", False))
    if include_plant:
        entities.extend(SolarmanPlantAggregateSensor(coordinator, entry, key) for key in ("generation_power", "energy_today", "energy_total"))
    for device_sn in coordinator.selected_device_sns:
        entities.extend(SolarmanCanonicalSensor(coordinator, entry, device_sn, key) for key in CANONICAL_SENSORS)
        payload = coordinator.data.get("devices", {}).get(device_sn, {}) if coordinator.data else {}
        for channel in (payload.get("panels") or {}).keys():
            entities.append(SolarmanPanelPowerSensor(coordinator, entry, device_sn, channel))
            entities.append(SolarmanPanelCapacitySensor(coordinator, entry, device_sn, channel))
            entities.append(SolarmanPanelEfficiencySensor(coordinator, entry, device_sn, channel))
    async_add_entities(entities)


class SolarmanBaseEntity(CoordinatorEntity[SolarmanDataCoordinator]):
    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, device_sn: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.device_sn = device_sn

    @property
    def device_info(self) -> DeviceInfo:
        topo = self.coordinator.get_device_topology(self.device_sn)
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_sn)},
            name=self.coordinator.device_display_name(self.device_sn),
            manufacturer="Solarman",
            model=str(topo.get("deviceModel") or topo.get("model") or topo.get("deviceType") or "Micro Inverter"),
            serial_number=self.device_sn,
            via_device=(DOMAIN, f"plant_{self.entry.data.get(CONF_PLANT_ID)}"),
        )

    def common_attrs(self) -> dict[str, Any]:
        topo = self.coordinator.get_device_topology(self.device_sn)
        return {
            ATTR_DEVICE_SN: self.device_sn,
            ATTR_DEVICE_ID: topo.get("deviceId") or topo.get("id"),
            ATTR_DEVICE_NAME: self.coordinator.device_display_name(self.device_sn),
            ATTR_PLANT_ID: self.entry.data.get(CONF_PLANT_ID),
            ATTR_SOURCE: "device",
        }


class SolarmanCanonicalSensor(SolarmanBaseEntity, SensorEntity):
    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, device_sn: str, metric_key: str) -> None:
        super().__init__(coordinator, entry, device_sn)
        name, device_class, state_class, unit = CANONICAL_SENSORS[metric_key]
        self.metric_key = metric_key
        self._attr_unique_id = f"{entry.entry_id}_{device_sn}_{metric_key}"
        self._attr_name = f"{self.coordinator.device_display_name(device_sn)} {name}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        payload = (self.coordinator.data or {}).get("devices", {}).get(self.device_sn, {})
        canonical = payload.get("canonical")
        return getattr(canonical, self.metric_key, None) if canonical else None

    @property
    def extra_state_attributes(self):
        attrs = self.common_attrs()
        attrs[ATTR_RAW_KEY] = self.metric_key
        return attrs


class SolarmanPanelPowerSensor(SolarmanBaseEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, device_sn: str, channel: str) -> None:
        super().__init__(coordinator, entry, device_sn)
        self.channel = channel
        self._attr_unique_id = f"{entry.entry_id}_{device_sn}_panel_{channel}_power"
        self._attr_name = f"{self.coordinator.device_display_name(device_sn)} Placa {channel} geração atual"

    @property
    def native_value(self):
        return self._panel().current_power_w if self._panel() else None

    @property
    def extra_state_attributes(self):
        attrs = self.common_attrs()
        attrs[ATTR_CHANNEL] = self.channel
        return attrs

    def _panel(self):
        return ((self.coordinator.data or {}).get("devices", {}).get(self.device_sn, {}).get("panels") or {}).get(self.channel)


class SolarmanPanelCapacitySensor(SolarmanBaseEntity, SensorEntity):
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, device_sn: str, channel: str) -> None:
        super().__init__(coordinator, entry, device_sn)
        self.channel = channel
        self._attr_unique_id = f"{entry.entry_id}_{device_sn}_panel_{channel}_capacity"
        self._attr_name = f"{self.coordinator.device_display_name(device_sn)} Placa {channel} capacidade nominal"

    @property
    def native_value(self):
        return self._panel().rated_capacity_w if self._panel() else None

    @property
    def extra_state_attributes(self):
        attrs = self.common_attrs()
        attrs[ATTR_CHANNEL] = self.channel
        return attrs

    def _panel(self):
        return ((self.coordinator.data or {}).get("devices", {}).get(self.device_sn, {}).get("panels") or {}).get(self.channel)


class SolarmanPanelEfficiencySensor(SolarmanBaseEntity, SensorEntity):
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, device_sn: str, channel: str) -> None:
        super().__init__(coordinator, entry, device_sn)
        self.channel = channel
        self._attr_unique_id = f"{entry.entry_id}_{device_sn}_panel_{channel}_efficiency"
        self._attr_name = f"{self.coordinator.device_display_name(device_sn)} Placa {channel} eficiência"

    @property
    def native_value(self):
        panel = self._panel()
        return panel.efficiency_percent if panel else None

    @property
    def extra_state_attributes(self):
        attrs = self.common_attrs()
        attrs[ATTR_CHANNEL] = self.channel
        return attrs

    def _panel(self):
        return ((self.coordinator.data or {}).get("devices", {}).get(self.device_sn, {}).get("panels") or {}).get(self.channel)


class SolarmanBudgetSensor(CoordinatorEntity[SolarmanDataCoordinator], SensorEntity):
    _attr_native_unit_of_measurement = "req/ano"

    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_budget"
        self._attr_name = "Solarman consumo anual estimado de requests"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("meta", {}).get("requests_per_year")

    @property
    def extra_state_attributes(self):
        return (self.coordinator.data or {}).get("meta", {})

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


class SolarmanPlantAggregateSensor(CoordinatorEntity[SolarmanDataCoordinator], SensorEntity):
    def __init__(self, coordinator: SolarmanDataCoordinator, entry: ConfigEntry, metric_key: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.metric_key = metric_key
        name, device_class, state_class, unit = CANONICAL_SENSORS[metric_key]
        self._attr_unique_id = f"{entry.entry_id}_plant_{metric_key}"
        self._attr_name = f"Planta {name}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        total = 0.0
        found = False
        for payload in ((self.coordinator.data or {}).get("devices") or {}).values():
            canonical = payload.get("canonical")
            value = getattr(canonical, self.metric_key, None) if canonical else None
            if value is not None:
                total += float(value)
                found = True
        return round(total, 3) if found else None

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

    @property
    def extra_state_attributes(self):
        return {"source": "aggregated_devices", "plant_id": self.entry.data.get(CONF_PLANT_ID)}
