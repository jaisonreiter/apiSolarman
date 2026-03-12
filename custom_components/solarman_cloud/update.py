from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_GITHUB_REPO, DOMAIN


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    repo = entry.options.get(CONF_GITHUB_REPO, entry.data.get(CONF_GITHUB_REPO, "")).strip()
    if repo:
        async_add_entities([SolarmanGitHubUpdateEntity(hass, entry, repo)])


class SolarmanGitHubUpdateEntity(UpdateEntity):
    _attr_supported_features = UpdateEntityFeature.RELEASE_NOTES

    def __init__(self, hass, entry: ConfigEntry, repo: str) -> None:
        self.hass = hass
        self.entry = entry
        self.repo = repo.replace("https://github.com/", "").strip("/")
        self._attr_name = "Solarman Cloud atualização da integração"
        self._attr_unique_id = f"{entry.entry_id}_github_update"
        self._attr_installed_version = "3.0.0"

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        async with session.get(url) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
        self._attr_latest_version = data.get("tag_name")
        self._attr_release_url = data.get("html_url")
        self._attr_release_summary = data.get("body")
