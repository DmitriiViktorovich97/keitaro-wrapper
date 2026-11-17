import os
from typing import Any

import httpx


class KeitaroError(Exception):
    """Ошибка при вызове Keitaro Admin API."""


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/") + "/admin_api/v1"
        self._headers = {"Api-Key": api_key, "Accept": "application/json"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method, f"{self.base_url}{path}",
                    headers=self._headers, **kwargs,
                )
        except httpx.HTTPError as e:
            raise KeitaroError(f"Keitaro недоступен: {e}") from e
        if resp.status_code >= 400:
            raise KeitaroError(f"{method} {path} -> {resp.status_code}: {resp.text}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # --- справочники ---
    async def list_domains(self) -> list[dict]:
        return await self._request("GET", "/domains")

    async def list_groups(self) -> list[dict]:
        return await self._request("GET", "/groups", params={"type": "campaigns"})

    async def list_traffic_sources(self) -> list[dict]:
        return await self._request("GET", "/traffic_sources")

    async def list_offers(self) -> list[dict]:
        return await self._request("GET", "/offers")

    # --- кампании и потоки ---
    async def create_campaign(self, payload: dict) -> dict:
        return await self._request("POST", "/campaigns", json=payload)

    async def delete_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    async def create_stream(self, payload: dict) -> dict:
        return await self._request("POST", "/streams", json=payload)

    async def get_stream(self, stream_id: int) -> dict:
        return await self._request("GET", f"/streams/{stream_id}")

    async def update_stream(self, stream_id: int, payload: dict) -> dict:
        # Admin API v1 обновляет сущности через PUT, а не POST
        return await self._request("PUT", f"/streams/{stream_id}", json=payload)


def get_keitaro_client() -> KeitaroClient:
    url = os.environ.get("KEITARO_URL")
    key = os.environ.get("KEITARO_API_KEY")
    if not url or not key:
        raise RuntimeError("KEITARO_URL and KEITARO_API_KEY must be set")
    return KeitaroClient(url, key)
