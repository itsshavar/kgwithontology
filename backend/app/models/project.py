from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_profile_id: Mapped[int | None] = mapped_column(ForeignKey("domain_profiles.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    domain_profile = relationship("DomainProfile", back_populates="projects")
    documents = relationship("SourceDocument", back_populates="project", cascade="all, delete-orphan")
    ontology_classes = relationship("OntologyClass", back_populates="project", cascade="all, delete-orphan")
    ontology_properties = relationship("OntologyProperty", back_populates="project", cascade="all, delete-orphan")
    entities = relationship("KGEntity", back_populates="project", cascade="all, delete-orphan")
    relation_instances = relationship("RelationInstance", back_populates="project", cascade="all, delete-orphan")
