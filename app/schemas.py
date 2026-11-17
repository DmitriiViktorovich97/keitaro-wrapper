from pydantic import BaseModel, ConfigDict, Field, field_validator


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    geo: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    offer_id: int
    domain_id: int
    group_id: int
    source_id: int

    @field_validator("geo")
    @classmethod
    def upper_geo(cls, v: str) -> str:
        return v.upper()


class OfferAdd(BaseModel):
    offer_id: int


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    geo: str
    keitaro_campaign_id: int


class OfferRead(BaseModel):
    """Оффер кампании: данные из БД + актуальные доля и название из Keitaro."""

    keitaro_offer_id: int
    name: str | None = None
    share: int
