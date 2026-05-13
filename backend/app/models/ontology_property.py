from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OntologyProperty(Base):
    __tablename__ = "ontology_properties"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_ontology_property_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    property_type: Mapped[str] = mapped_column(String(50), default="object", nullable=False)
    domain_class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_classes.id"), nullable=True)
    range_class_id: Mapped[int | None] = mapped_column(ForeignKey("ontology_classes.id"), nullable=True)
    range_datatype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="ontology_properties")
