from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DomainProfile(Base):
    __tablename__ = "domain_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed_schema: Mapped[str | None] = mapped_column(Text, nullable=True)
    relation_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="domain_profile")
