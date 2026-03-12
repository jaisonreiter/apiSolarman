from __future__ import annotations

import re
from typing import Any

from .const import CANONICAL_MAP
from .helpers import first_value, normalize_key
from .models import CanonicalMetrics, PanelMetric

_PANEL_PATTERNS = [
    re.compile(r"^(?:pv|panel|string|channel|ch)(\d+)(?:_)?(?:power|p|outputpower)$", re.I),
    re.compile(r"^(?:pv|panel|string|channel|ch)(\d+)(?:_)?(?:status|state)$", re.I),
    re.compile(r"^(?:pv|panel|string|channel|ch)(\d+)(?:_)?(?:capacity|rated|nominal|wp)$", re.I),
]


def flatten_current_data(payload: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for item in payload.get("dataList", []) or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or item.get("name") or "")
        if not key:
            continue
        value = item.get("value")
        flat[key] = value
        unit = item.get("unit")
        if unit:
            flat[f"{key}__unit"] = unit
        label = item.get("name")
        if label:
            flat[f"{key}__name"] = label
    for key, value in payload.items():
        if key == "dataList":
            continue
        if not isinstance(value, (dict, list)):
            flat[key] = value
    return flat


def parse_canonical_metrics(flat: dict[str, Any]) -> CanonicalMetrics:
    return CanonicalMetrics(
        generation_power=_as_float(first_value(flat, CANONICAL_MAP["generation_power"])),
        energy_today=_as_float(first_value(flat, CANONICAL_MAP["energy_today"])),
        energy_total=_as_float(first_value(flat, CANONICAL_MAP["energy_total"])),
        inverter_temperature=_as_float(first_value(flat, CANONICAL_MAP["inverter_temperature"])),
        grid_voltage=_as_float(first_value(flat, CANONICAL_MAP["grid_voltage"])),
        grid_current=_as_float(first_value(flat, CANONICAL_MAP["grid_current"])),
        grid_frequency=_as_float(first_value(flat, CANONICAL_MAP["grid_frequency"])),
        power_factor=_as_float(first_value(flat, CANONICAL_MAP["power_factor"])),
        status=_as_str(first_value(flat, CANONICAL_MAP["status"])),
    )


def parse_panel_metrics(flat: dict[str, Any], default_capacity_w: int) -> dict[str, PanelMetric]:
    panels: dict[str, PanelMetric] = {}
    for raw_key, value in flat.items():
        if raw_key.endswith("__unit") or raw_key.endswith("__name"):
            continue
        key = normalize_key(raw_key)
        for pattern in _PANEL_PATTERNS:
            match = pattern.match(key)
            if not match:
                continue
            channel = match.group(1)
            panel = panels.setdefault(channel, PanelMetric(channel=channel, rated_capacity_w=float(default_capacity_w), raw={}))
            panel.raw[raw_key] = value
            if any(token in key for token in ["power", "outputpower", "_p"]):
                panel.current_power_w = _as_float(value)
                if panel.current_power_w is not None and panel.status_on is None:
                    panel.status_on = panel.current_power_w > 1
            elif any(token in key for token in ["status", "state"]):
                panel.status_on = _status_to_bool(value)
            elif any(token in key for token in ["capacity", "rated", "nominal", "wp"]):
                cap = _as_float(value)
                if cap:
                    panel.rated_capacity_w = cap
            break
    return panels


def _as_float(value: Any) -> float | None:
    try:
        if value in (None, "", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _status_to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "on", "true", "running", "online"}:
        return True
    if text in {"0", "off", "false", "stopped", "offline"}:
        return False
    return None
