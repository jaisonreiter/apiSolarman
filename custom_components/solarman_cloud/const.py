from __future__ import annotations

DOMAIN = "solarman_cloud"
PLATFORMS = ["sensor", "binary_sensor", "button", "update"]

DEFAULT_BASE_URL = "https://globalapi.solarmanpv.com"
DEFAULT_LOGIN_TYPE = "email"
DEFAULT_UPDATE_MINUTES = 6
DEFAULT_START_TIME = "05:30"
DEFAULT_END_TIME = "19:30"
DEFAULT_REQUEST_LIMIT = 200000
DEFAULT_SAFE_PERCENT = 90
DEFAULT_INCLUDE_PLANT_SENSORS = False
DEFAULT_DEFAULT_PANEL_CAPACITY_W = 550
DEFAULT_GITHUB_REPO = ""
DEFAULT_DEVICE_TYPE = "MICRO_INVERTER"

CONF_BASE_URL = "base_url"
CONF_APP_ID = "app_id"
CONF_APP_SECRET = "app_secret"
CONF_LOGIN_TYPE = "login_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ORG_ID = "org_id"
CONF_PLANT_ID = "plant_id"
CONF_DEVICE_TYPE = "device_type"
CONF_SELECTED_DEVICE_SNS = "selected_device_sns"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"
CONF_START_TIME = "start_time"
CONF_END_TIME = "end_time"
CONF_REQUEST_LIMIT = "request_limit"
CONF_SAFE_PERCENT = "safe_percent"
CONF_INCLUDE_PLANT_SENSORS = "include_plant_sensors"
CONF_DEFAULT_PANEL_CAPACITY_W = "default_panel_capacity_w"
CONF_GITHUB_REPO = "github_repo"
CONF_GITHUB_BRANCH = "github_branch"
CONF_TOPOLOGY = "topology"
CONF_HASH_PASSWORD = "hash_password"

DATA_API = "api"
DATA_COORDINATOR = "coordinator"
DATA_TOPOLOGY = "topology"
DATA_UPDATE_METADATA = "update_metadata"

ATTR_DEVICE_SN = "device_sn"
ATTR_DEVICE_ID = "device_id"
ATTR_PLANT_ID = "plant_id"
ATTR_SOURCE = "source"
ATTR_RAW_KEY = "raw_key"
ATTR_DEVICE_NAME = "device_name"
ATTR_CHANNEL = "channel"
ATTR_CAPACITY_W = "capacity_w"
ATTR_REQUESTS_PER_DAY = "requests_per_day"
ATTR_REQUESTS_PER_YEAR = "requests_per_year"
ATTR_BUDGET_LIMIT = "budget_limit"
ATTR_SAFE_LIMIT = "safe_limit"
ATTR_ESTIMATED_PERCENT = "estimated_percent"
ATTR_WINDOW_MINUTES = "window_minutes"

LOGIN_TYPES = ["email", "username", "mobile"]
DEVICE_TYPES = ["INVERTER", "MICRO_INVERTER", "COLLECTOR"]

CANONICAL_MAP = {
    "generation_power": ["pac", "generationpower", "apo_t1", "activepower", "outputpower", "power"],
    "energy_today": ["etoday", "generationtoday", "edty_ge1", "eday", "today_energy"],
    "energy_total": ["etotal", "generationtotal", "et_ge0", "total_energy"],
    "inverter_temperature": ["temperature", "inv_t0", "temp", "device_temp"],
    "grid_voltage": ["vac", "av1", "gridvoltage", "ac_voltage", "voltage"],
    "grid_current": ["iac", "gridcurrent", "ac_current", "current"],
    "grid_frequency": ["fac", "freq", "frequency", "gridfreq"],
    "power_factor": ["pf", "powerfactor"],
    "status": ["status", "run_state", "state"],
}
