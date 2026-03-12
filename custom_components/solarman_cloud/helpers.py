from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def normalize_key(value: str) -> str:
    return slugify(value or "")


def parse_hhmm(value: str) -> tuple[int, int]:
    hours, minutes = value.split(":", 1)
    return int(hours), int(minutes)


def time_window_minutes(start_time: str, end_time: str) -> int:
    sh, sm = parse_hhmm(start_time)
    eh, em = parse_hhmm(end_time)
    start = sh * 60 + sm
    end = eh * 60 + em
    if end >= start:
        return end - start
    return (24 * 60 - start) + end


@dataclass(slots=True)
class RequestBudget:
    request_limit: int
    safe_percent: int
    device_count: int
    update_interval_minutes: int
    start_time: str
    end_time: str

    @property
    def safe_limit(self) -> int:
        return int(self.request_limit * (self.safe_percent / 100))

    @property
    def window_minutes(self) -> int:
        return time_window_minutes(self.start_time, self.end_time)

    @property
    def cycles_per_day(self) -> int:
        return self.window_minutes // self.update_interval_minutes

    @property
    def requests_per_cycle(self) -> int:
        return self.device_count

    @property
    def requests_per_day(self) -> int:
        return self.cycles_per_day * self.requests_per_cycle

    @property
    def requests_per_year(self) -> int:
        return self.requests_per_day * 365

    @property
    def estimated_percent(self) -> float:
        if self.request_limit <= 0:
            return 0.0
        return round((self.requests_per_year / self.request_limit) * 100, 2)

    @property
    def within_safe_limit(self) -> bool:
        return self.requests_per_year <= self.safe_limit

    @property
    def minimum_interval_minutes(self) -> int:
        if self.device_count <= 0 or self.safe_limit <= 0:
            return 1
        numerator = 365 * self.window_minutes * self.device_count
        return max(1, ceil(numerator / self.safe_limit))


def infer_device_name(device: dict[str, Any]) -> str:
    for key in ("deviceName", "name", "sn", "deviceSn"):
        if device.get(key):
            return str(device[key])
    return "Solarman Device"


def infer_device_sn(device: dict[str, Any]) -> str:
    for key in ("deviceSn", "sn", "device_sn"):
        if device.get(key):
            return str(device[key])
    return "unknown"


def first_value(mapping: dict[str, Any], keys: Iterable[str]) -> Any:
    normalized = {normalize_key(k): v for k, v in mapping.items()}
    for key in keys:
        if normalize_key(key) in normalized:
            return normalized[normalize_key(key)]
    return None
