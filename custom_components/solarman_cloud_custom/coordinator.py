from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarmanCloudApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarmanCloudCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, api: SolarmanCloudApi, interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            return await self.api.fetch_all()
        except Exception as exc:
            raise UpdateFailed(f"Falha ao atualizar dados da Solarman: {exc}") from exc
