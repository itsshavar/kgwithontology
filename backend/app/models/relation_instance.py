from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RelationInstance(Base):
    __tablename__ = "relation_instances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    subject_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False, index=True)
    predicate_id: Mapped[int] = mapped_column(ForeignKey("ontology_properties.id"), nullable=False, index=True)
    object_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True, index=True)
    object_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="relation_instances")
    source_document = relationship("SourceDocument", back_populates="relation_instances")
