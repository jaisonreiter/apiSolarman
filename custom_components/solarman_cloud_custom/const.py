from __future__ import annotations

DOMAIN = "solarman_cloud_custom"
PLATFORMS = ["sensor"]

CONF_BASE_URL = "base_url"
CONF_APP_ID = "app_id"
CONF_APP_SECRET = "app_secret"
CONF_LOGIN_TYPE = "login_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ORG_ID = "org_id"
CONF_PLANT_ID = "plant_id"
CONF_DEVICE_SN = "device_sn"
CONF_DEVICE_TYPE = "device_type"
CONF_POLL_INTERVAL = "poll_interval"
CONF_LANGUAGE = "language"
CONF_PASSWORD_ALREADY_SHA256 = "password_already_sha256"
CONF_INCLUDE_PLANT_SENSORS = "include_plant_sensors"

DEFAULT_BASE_URL = "https://globalapi.solarmanpv.com"
DEFAULT_LANGUAGE = "en"
DEFAULT_POLL_INTERVAL = 300
DEFAULT_INCLUDE_PLANT_SENSORS = True
DEFAULT_DEVICE_TYPE = "INVERTER"

TOKEN_ENDPOINT = "/account/v1.0/token"
PLANT_LIST_ENDPOINT = "/station/v1.0/list"
PLANT_REALTIME_ENDPOINT = "/station/v1.0/realTime"
STATION_DEVICE_LIST_ENDPOINT = "/station/v1.0/device"
DEVICE_REALTIME_ENDPOINT = "/device/v1.0/currentData"

LOGIN_EMAIL = "email"
LOGIN_USERNAME = "username"
LOGIN_MOBILE = "mobile"
LOGIN_TYPES = [LOGIN_EMAIL, LOGIN_USERNAME, LOGIN_MOBILE]

DEVICE_TYPE_INVERTER = "INVERTER"
DEVICE_TYPE_MICRO_INVERTER = "MICRO_INVERTER"
DEVICE_TYPE_COLLECTOR = "COLLECTOR"
DEVICE_TYPES = [DEVICE_TYPE_INVERTER, DEVICE_TYPE_MICRO_INVERTER, DEVICE_TYPE_COLLECTOR]

ATTR_DEVICE_SN = "device_sn"
ATTR_DEVICE_ID = "device_id"
ATTR_PLANT_ID = "plant_id"
ATTR_SOURCE = "source"
ATTR_RAW_KEY = "raw_key"
