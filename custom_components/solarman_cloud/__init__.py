from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolarmanAPI
from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_BASE_URL,
    CONF_HASH_PASSWORD,
    CONF_LOGIN_TYPE,
    CONF_ORG_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    DATA_API,
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SolarmanDataCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = SolarmanAPI(
        session,
        entry.data[CONF_BASE_URL],
        entry.data[CONF_APP_ID],
        entry.data[CONF_APP_SECRET],
        entry.data[CONF_LOGIN_TYPE],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_ORG_ID),
        hash_password=entry.data.get(CONF_HASH_PASSWORD, False),
    )
    await api.authenticate()
    coordinator = SolarmanDataCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_API: api,
        DATA_COORDINATOR: coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
