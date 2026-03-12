from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientResponseError

from .const import (
    CONF_APP_ID,
    CONF_APP_SECRET,
    CONF_BASE_URL,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_LANGUAGE,
    CONF_LOGIN_TYPE,
    CONF_ORG_ID,
    CONF_PASSWORD,
    CONF_PASSWORD_ALREADY_SHA256,
    CONF_PLANT_ID,
    CONF_USERNAME,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_LANGUAGE,
    DEVICE_REALTIME_ENDPOINT,
    PLANT_LIST_ENDPOINT,
    PLANT_REALTIME_ENDPOINT,
    STATION_DEVICE_LIST_ENDPOINT,
    TOKEN_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class SolarmanApiError(Exception):
    """Raised when Solarman API returns an error."""


class SolarmanCloudApi:
    def __init__(self, session: aiohttp.ClientSession, config: dict[str, Any]) -> None:
        self._session = session
        self._config = config
        self._access_token: str | None = None
        self._token_lock = asyncio.Lock()
        self._selected_plant_id: int | None = None
        self._selected_device_sn: str | None = None
        self._selected_device_id: int | None = None

    @property
    def selected_plant_id(self) -> int | None:
        return self._selected_plant_id

    @property
    def selected_device_sn(self) -> str | None:
        return self._selected_device_sn

    @property
    def selected_device_id(self) -> int | None:
        return self._selected_device_id

    def _base_url(self) -> str:
        return str(self._config.get(CONF_BASE_URL)).rstrip("/")

    def _build_url(self, path: str, *, include_app_id: bool = False) -> str:
        query = {"language": self._config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)}
        if include_app_id:
            query["appId"] = self._config[CONF_APP_ID]
        return f"{self._base_url()}{path}?{urlencode(query)}"

    def _hashed_password(self) -> str:
        password = str(self._config[CONF_PASSWORD])
        if self._config.get(CONF_PASSWORD_ALREADY_SHA256, False):
            return password
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _login_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "appSecret": self._config[CONF_APP_SECRET],
            "password": self._hashed_password(),
        }
        payload[self._config[CONF_LOGIN_TYPE]] = self._config[CONF_USERNAME]
        org_id = self._config.get(CONF_ORG_ID)
        if org_id not in (None, ""):
            payload["orgId"] = int(org_id)
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        include_app_id: bool = False,
        use_auth: bool = True,
        retry_on_401: bool = True,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if use_auth:
            await self.ensure_token()
            headers["Authorization"] = f"bearer {self._access_token}"

        url = self._build_url(path, include_app_id=include_app_id)
        async with self._session.request(method, url, json=payload or {}, headers=headers, timeout=30) as resp:
            text = await resp.text()
            if resp.status == 401 and use_auth and retry_on_401:
                self._access_token = None
                await self.ensure_token(force_refresh=True)
                return await self._request(
                    method,
                    path,
                    payload,
                    include_app_id=include_app_id,
                    use_auth=use_auth,
                    retry_on_401=False,
                )
            if resp.status >= 400:
                raise ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message=text,
                    headers=resp.headers,
                )
            data = await resp.json(content_type=None)

        if isinstance(data, dict) and data.get("success") is False:
            code = str(data.get("code", ""))
            msg = data.get("msg") or code or "Solarman API error"
            if retry_on_401 and code.startswith("21") and use_auth:
                self._access_token = None
                await self.ensure_token(force_refresh=True)
                return await self._request(
                    method,
                    path,
                    payload,
                    include_app_id=include_app_id,
                    use_auth=use_auth,
                    retry_on_401=False,
                )
            raise SolarmanApiError(msg)
        return data

    async def ensure_token(self, force_refresh: bool = False) -> None:
        if self._access_token and not force_refresh:
            return
        async with self._token_lock:
            if self._access_token and not force_refresh:
                return
            data = await self._request(
                "POST",
                TOKEN_ENDPOINT,
                self._login_payload(),
                include_app_id=True,
                use_auth=False,
                retry_on_401=False,
            )
            token = data.get("access_token") or data.get("accessToken")
            if not token:
                raise SolarmanApiError("Token não retornado pela API da Solarman.")
            self._access_token = token

    async def plant_list(self) -> list[dict[str, Any]]:
        data = await self._request("POST", PLANT_LIST_ENDPOINT, {"page": 1, "size": 100})
        return data.get("stationList") or []

    async def plant_realtime(self, plant_id: int) -> dict[str, Any]:
        return await self._request("POST", PLANT_REALTIME_ENDPOINT, {"stationId": plant_id})

    async def station_devices(self, plant_id: int) -> list[dict[str, Any]]:
        payload = {
            "stationId": plant_id,
            "page": 1,
            "size": 100,
            "deviceType": self._config.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE),
        }
        data = await self._request("POST", STATION_DEVICE_LIST_ENDPOINT, payload)
        return data.get("deviceListItems") or []

    async def device_realtime(self, device_sn: str, device_id: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"deviceSn": device_sn}
        if device_id is not None:
            payload["deviceId"] = device_id
        return await self._request("POST", DEVICE_REALTIME_ENDPOINT, payload)

    async def discover(self) -> dict[str, Any]:
        plants = await self.plant_list()
        if not plants:
            raise SolarmanApiError("Nenhuma planta encontrada para a conta informada.")

        configured_plant_id = self._config.get(CONF_PLANT_ID)
        plant_id = int(configured_plant_id) if configured_plant_id not in (None, "") else None
        selected_plant = next((p for p in plants if plant_id and int(p.get("id", 0)) == plant_id), None)
        if selected_plant is None:
            selected_plant = plants[0]
            plant_id = int(selected_plant["id"])

        devices = await self.station_devices(plant_id)
        if not devices:
            raise SolarmanApiError(
                f"Nenhum dispositivo do tipo {self._config.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)} foi encontrado na planta {plant_id}."
            )

        configured_sn = self._config.get(CONF_DEVICE_SN)
        selected_device = next((d for d in devices if configured_sn and d.get("deviceSn") == configured_sn), None)
        if selected_device is None:
            selected_device = devices[0]

        self._selected_plant_id = plant_id
        self._selected_device_sn = selected_device.get("deviceSn")
        self._selected_device_id = selected_device.get("deviceId")
        return {
            "plant": selected_plant,
            "devices": devices,
            "selected_device": selected_device,
        }

    async def fetch_all(self) -> dict[str, Any]:
        await self.ensure_token()
        if self._selected_plant_id is None or self._selected_device_sn is None:
            await self.discover()

        plant_data: dict[str, Any] = {}
        if self._selected_plant_id is not None:
            try:
                plant_data = await self.plant_realtime(self._selected_plant_id)
            except Exception as exc:
                _LOGGER.warning("Falha ao obter dados da planta: %s", exc)

        device_data = await self.device_realtime(self._selected_device_sn, self._selected_device_id)
        return {
            "plant": plant_data,
            "device": device_data,
            "selected": {
                "plant_id": self._selected_plant_id,
                "device_sn": self._selected_device_sn,
                "device_id": self._selected_device_id,
                "device_type": self._config.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE),
            },
        }

    async def async_validate(self) -> dict[str, Any]:
        await self.ensure_token()
        discovered = await self.discover()
        device_data = await self.device_realtime(self._selected_device_sn, self._selected_device_id)
        return {"discovered": discovered, "device": device_data}
