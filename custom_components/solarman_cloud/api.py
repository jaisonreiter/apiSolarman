from __future__ import annotations

import hashlib
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import DEFAULT_BASE_URL

_LOGGER = logging.getLogger(__name__)


class SolarmanApiError(Exception):
    """Base API error."""


class SolarmanAuthError(SolarmanApiError):
    """Authentication failed."""


class SolarmanAPI:
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        app_id: str,
        app_secret: str,
        login_type: str,
        username: str,
        password: str,
        org_id: str | None = None,
        hash_password: bool = False,
    ) -> None:
        self._session = session
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._app_id = app_id
        self._app_secret = app_secret
        self._login_type = login_type
        self._username = username
        self._password = password if hash_password else hashlib.sha256(password.encode()).hexdigest()
        self._org_id = org_id
        self._token: str | None = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth:
            if not self._token:
                await self.authenticate()
            headers["Authorization"] = f"Bearer {self._token}"

        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(method, url, headers=headers, json=json_body) as resp:
                data = await resp.json(content_type=None)
        except ClientError as err:
            raise SolarmanApiError(f"Network error calling Solarman API: {err}") from err

        if resp.status == 401:
            self._token = None
            raise SolarmanAuthError("Unauthorized")

        if resp.status >= 400:
            raise SolarmanApiError(f"HTTP {resp.status}: {data}")

        if isinstance(data, dict):
            code = data.get("code")
            success = data.get("success")
            if code not in (None, 200, "200") and success not in (None, True):
                message = data.get("msg") or data.get("message") or str(data)
                raise SolarmanApiError(message)
        return data

    async def authenticate(self) -> str:
        payload: dict[str, Any] = {
            "appSecret": self._app_secret,
            self._login_type: self._username,
            "password": self._password,
        }
        if self._org_id:
            payload["orgId"] = self._org_id
        data = await self._request(
            "POST",
            f"/account/v1.0/token?appId={self._app_id}",
            json_body=payload,
            auth=False,
        )
        token = (
            data.get("access_token")
            or data.get("token")
            or (data.get("data") or {}).get("access_token")
            or (data.get("data") or {}).get("token")
        )
        if not token:
            raise SolarmanAuthError(f"Token not found in response: {data}")
        self._token = token
        return token

    async def list_plants(self) -> list[dict[str, Any]]:
        payload = {"page": 1, "size": 100}
        data = await self._request("POST", "/station/v1.0/list", json_body=payload)
        plants = data.get("stationList") or (data.get("data") or {}).get("stationList") or data.get("data") or []
        return plants if isinstance(plants, list) else []

    async def get_plant_basic(self, plant_id: int | str) -> dict[str, Any]:
        payload = {"plantId": int(plant_id)}
        data = await self._request("POST", "/station/v1.0/basic", json_body=payload)
        return data.get("data") or data

    async def list_plant_devices(self, plant_id: int | str) -> list[dict[str, Any]]:
        payload = {"plantId": int(plant_id), "page": 1, "size": 200}
        data = await self._request("POST", "/station/v1.0/device", json_body=payload)
        devices = data.get("deviceList") or (data.get("data") or {}).get("deviceList") or data.get("data") or []
        return devices if isinstance(devices, list) else []

    async def get_device_current_data(self, device_sn: str, device_type: str) -> dict[str, Any]:
        payload = {"deviceSn": device_sn, "deviceType": device_type}
        data = await self._request("POST", "/device/v1.0/currentData", json_body=payload)
        return data.get("data") or data
