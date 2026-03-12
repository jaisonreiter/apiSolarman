from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PanelMetric:
    channel: str
    current_power_w: float | None = None
    rated_capacity_w: float | None = None
    status_on: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def efficiency_percent(self) -> float | None:
        if self.current_power_w is None or not self.rated_capacity_w:
            return None
        if self.rated_capacity_w <= 0:
            return None
        return round((self.current_power_w / self.rated_capacity_w) * 100, 2)


@dataclass(slots=True)
class CanonicalMetrics:
    generation_power: float | None = None
    energy_today: float | None = None
    energy_total: float | None = None
    inverter_temperature: float | None = None
    grid_voltage: float | None = None
    grid_current: float | None = None
    grid_frequency: float | None = None
    power_factor: float | None = None
    status: str | None = None
