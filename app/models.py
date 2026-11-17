from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geo: Mapped[str] = mapped_column(String(2), nullable=False)
    keitaro_campaign_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    keitaro_domain_id: Mapped[int] = mapped_column(BigInteger)
    keitaro_group_id: Mapped[int] = mapped_column(BigInteger)
    keitaro_source_id: Mapped[int] = mapped_column(BigInteger)
    offer_stream_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("campaign_id", "keitaro_offer_id", name="uq_offer_per_campaign"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    keitaro_offer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    campaign: Mapped[Campaign] = relationship(back_populates="offers")
