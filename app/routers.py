from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.keitaro_client import KeitaroClient, get_keitaro_client
from app.models import Campaign
from app.schemas import CampaignCreate, CampaignRead, OfferAdd, OfferRead
from app.services import campaign_service as svc

router = APIRouter(prefix="/api")


# --- справочники Keitaro для выпадающих списков ---
@router.get("/keitaro/domains")
async def domains(kt: KeitaroClient = Depends(get_keitaro_client)):
    return [{"id": d["id"], "name": d.get("name")} for d in await kt.list_domains()]


@router.get("/keitaro/groups")
async def groups(kt: KeitaroClient = Depends(get_keitaro_client)):
    items = await kt.list_groups()
    # группы бывают для кампаний/офферов/лендингов — нужны только кампании
    return [
        {"id": g["id"], "name": g.get("name")}
        for g in items
        if g.get("type", "campaigns") == "campaigns"
    ]


@router.get("/keitaro/sources")
async def sources(kt: KeitaroClient = Depends(get_keitaro_client)):
    return [
        {"id": s["id"], "name": s.get("name")} for s in await kt.list_traffic_sources()
    ]


@router.get("/keitaro/offers")
async def kt_offers(kt: KeitaroClient = Depends(get_keitaro_client)):
    return [{"id": o["id"], "name": o.get("name")} for o in await kt.list_offers()]


# --- кампании ---
@router.post("/campaigns", response_model=CampaignRead, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    kt: KeitaroClient = Depends(get_keitaro_client),
):
    return await svc.create_campaign(db, kt, data)


@router.get("/campaigns", response_model=list[CampaignRead])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.id.desc()))
    return result.scalars().all()


# --- офферы кампании ---
@router.get("/campaigns/{campaign_id}/offers", response_model=list[OfferRead])
async def list_offers(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    kt: KeitaroClient = Depends(get_keitaro_client),
):
    return await svc.list_offers(db, kt, campaign_id)


@router.post("/campaigns/{campaign_id}/offers", response_model=list[OfferRead], status_code=201)
async def add_offer(
    campaign_id: int,
    data: OfferAdd,
    db: AsyncSession = Depends(get_db),
    kt: KeitaroClient = Depends(get_keitaro_client),
):
    await svc.add_offer(db, kt, campaign_id, data.offer_id)
    return await svc.list_offers(db, kt, campaign_id)


@router.delete("/campaigns/{campaign_id}/offers/{offer_id}", response_model=list[OfferRead])
async def remove_offer(
    campaign_id: int,
    offer_id: int,
    db: AsyncSession = Depends(get_db),
    kt: KeitaroClient = Depends(get_keitaro_client),
):
    await svc.remove_offer(db, kt, campaign_id, offer_id)
    return await svc.list_offers(db, kt, campaign_id)
