import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.keitaro_client import KeitaroClient, KeitaroError
from app.models import Campaign, Offer
from app.schemas import CampaignCreate

GOOGLE_URL = "https://www.google.com"


class ServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def split_shares(offer_ids: list[int]) -> list[dict]:
    """Делит 100% поровну; остаток от деления достаётся первым офферам,
    чтобы сумма всегда была ровно 100."""
    n = len(offer_ids)
    base, rest = divmod(100, n)
    return [
        {"offer_id": oid, "share": base + (1 if i < rest else 0), "state": "active"}
        for i, oid in enumerate(offer_ids)
    ]


async def create_campaign(
    db: AsyncSession, keitaro: KeitaroClient, data: CampaignCreate
) -> Campaign:
    created = await keitaro.create_campaign(
        {
            "name": data.name,
            "alias": secrets.token_hex(4),
            "type": "position",
            "state": "active",
            "domain_id": data.domain_id,
            "group_id": data.group_id,
            "traffic_source_id": data.source_id,
        }
    )
    kt_campaign_id = created["id"]

    try:
        # Поток 1: вся указанная страна -> Google
        await keitaro.create_stream(
            {
                "campaign_id": kt_campaign_id,
                "name": f"{data.geo} -> Google",
                "type": "regular",
                "schema": "redirect",
                "action_type": "http",
                "action_payload": GOOGLE_URL,
                "position": 1,
                "state": "active",
                "collect_clicks": True,
                "filters": [
                    {"name": "country", "mode": "accept", "payload": [data.geo]}
                ],
            }
        )
        # Поток 2: все остальные -> оффер
        offer_stream = await keitaro.create_stream(
            {
                "campaign_id": kt_campaign_id,
                "name": "Offers",
                "type": "regular",
                "action_type": "http",
                "schema": "landings",
                "position": 2,
                "state": "active",
                "collect_clicks": True,
                "offers": split_shares([data.offer_id]),
            }
        )

        campaign = Campaign(
            name=data.name,
            geo=data.geo,
            keitaro_campaign_id=kt_campaign_id,
            keitaro_domain_id=data.domain_id,
            keitaro_group_id=data.group_id,
            keitaro_source_id=data.source_id,
            offer_stream_id=offer_stream["id"],
            offers=[Offer(keitaro_offer_id=data.offer_id)],
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign
    except Exception:
        await db.rollback()
        # Не оставляем в Keitaro недособранную кампанию
        try:
            await keitaro.delete_campaign(kt_campaign_id)
        except KeitaroError:
            pass
        raise


async def _get_campaign(db: AsyncSession, campaign_id: int) -> Campaign:
    # FOR UPDATE: два одновременных add/remove не должны затирать друг друга
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id).with_for_update()
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise ServiceError(404, "Кампания не найдена")
    if campaign.offer_stream_id is None:
        raise ServiceError(409, "У кампании нет потока с офферами")
    return campaign


async def list_offers(
    db: AsyncSession, keitaro: KeitaroClient, campaign_id: int
) -> list[dict]:
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise ServiceError(404, "Кампания не найдена")
    if campaign.offer_stream_id is None:
        return []

    # Цифры берём из Keitaro — это источник правды по долям
    stream = await keitaro.get_stream(campaign.offer_stream_id)
    names = {o["id"]: o.get("name") for o in await keitaro.list_offers()}
    return [
        {
            "keitaro_offer_id": o["offer_id"],
            "name": names.get(o["offer_id"]),
            "share": o.get("share", 0),
        }
        for o in stream.get("offers", [])
    ]


async def add_offer(
    db: AsyncSession, keitaro: KeitaroClient, campaign_id: int, offer_id: int
) -> None:
    campaign = await _get_campaign(db, campaign_id)
    stream = await keitaro.get_stream(campaign.offer_stream_id)
    current = [o["offer_id"] for o in stream.get("offers", [])]
    if offer_id in current:
        raise ServiceError(409, "Оффер уже добавлен в кампанию")

    await keitaro.update_stream(
        campaign.offer_stream_id, {"offers": split_shares(current + [offer_id])}
    )
    db.add(Offer(campaign_id=campaign.id, keitaro_offer_id=offer_id))
    await db.commit()


async def remove_offer(
    db: AsyncSession, keitaro: KeitaroClient, campaign_id: int, offer_id: int
) -> None:
    campaign = await _get_campaign(db, campaign_id)
    stream = await keitaro.get_stream(campaign.offer_stream_id)
    current = [o["offer_id"] for o in stream.get("offers", [])]
    if offer_id not in current:
        raise ServiceError(404, "Оффера нет в кампании")
    if len(current) == 1:
        raise ServiceError(409, "Нельзя удалить последний оффер кампании")

    remaining = [o for o in current if o != offer_id]
    await keitaro.update_stream(
        campaign.offer_stream_id, {"offers": split_shares(remaining)}
    )
    result = await db.execute(
        select(Offer).where(
            Offer.campaign_id == campaign.id, Offer.keitaro_offer_id == offer_id
        )
    )
    for row in result.scalars():
        await db.delete(row)
    await db.commit()
