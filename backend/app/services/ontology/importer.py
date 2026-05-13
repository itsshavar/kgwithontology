from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty


class OntologyImportError(ValueError):
    """Raised when an ontology import payload is invalid."""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise OntologyImportError("Ontology payload fields 'classes' and 'properties' must be arrays.")


def import_ontology_payload(project_id: int, payload: dict[str, Any], db: Session) -> dict[str, Sequence[object] | int]:
    classes_payload = _as_list(payload.get("classes"))
    properties_payload = _as_list(payload.get("properties"))

    existing_classes = {
        item.name.lower(): item
        for item in db.scalars(
            select(OntologyClass).where(OntologyClass.project_id == project_id)
        ).all()
    }
    created_classes: list[OntologyClass] = []
    updated_classes: list[OntologyClass] = []

    for item in classes_payload:
        if not isinstance(item, dict):
            raise OntologyImportError("Each ontology class entry must be an object.")

        name = str(item.get("name", "")).strip()
        if not name:
            raise OntologyImportError("Each ontology class entry requires a 'name'.")

        class_obj = existing_classes.get(name.lower())
        if class_obj is None:
            class_obj = OntologyClass(
                project_id=project_id,
                name=name,
                label=item.get("label"),
                description=item.get("description"),
                status=item.get("status", "imported"),
                source=item.get("source", "import"),
                confidence=item.get("confidence"),
            )
            db.add(class_obj)
            db.flush()
            created_classes.append(class_obj)
            existing_classes[name.lower()] = class_obj
        else:
            class_obj.label = item.get("label", class_obj.label)
            class_obj.description = item.get("description", class_obj.description)
            class_obj.status = item.get("status", class_obj.status)
            class_obj.source = item.get("source", class_obj.source)
            class_obj.confidence = item.get("confidence", class_obj.confidence)
            updated_classes.append(class_obj)

    for item in classes_payload:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        class_obj = existing_classes[name.lower()]
        parent_name = str(
            item.get("parent_class_name") or item.get("parent") or item.get("parent_name") or ""
        ).strip()
        if parent_name:
            parent_obj = existing_classes.get(parent_name.lower())
            if parent_obj is None:
                raise OntologyImportError(
                    f"Parent class '{parent_name}' referenced by '{name}' was not found in the payload or project."
                )
            class_obj.parent_class_id = parent_obj.id

    existing_properties = {
        item.name.lower(): item
        for item in db.scalars(
            select(OntologyProperty).where(OntologyProperty.project_id == project_id)
        ).all()
    }
    created_properties: list[OntologyProperty] = []
    updated_properties: list[OntologyProperty] = []

    for item in properties_payload:
        if not isinstance(item, dict):
            raise OntologyImportError("Each ontology property entry must be an object.")

        name = str(item.get("name", "")).strip()
        if not name:
            raise OntologyImportError("Each ontology property entry requires a 'name'.")

        property_type = str(item.get("property_type") or item.get("type") or "object").strip().lower()
        if property_type not in {"object", "data"}:
            raise OntologyImportError(
                f"Ontology property '{name}' has invalid property_type '{property_type}'. Use 'object' or 'data'."
            )

        domain_name = str(item.get("domain_class_name") or item.get("domain") or "").strip()
        range_name = str(item.get("range_class_name") or item.get("range") or "").strip()
        domain_class_id = existing_classes.get(domain_name.lower()).id if domain_name and existing_classes.get(domain_name.lower()) else None
        range_class_id = existing_classes.get(range_name.lower()).id if property_type == "object" and range_name and existing_classes.get(range_name.lower()) else None
        range_datatype = item.get("range_datatype")

        property_obj = existing_properties.get(name.lower())
        if property_obj is None:
            property_obj = OntologyProperty(
                project_id=project_id,
                name=name,
                label=item.get("label"),
                description=item.get("description"),
                property_type=property_type,
                domain_class_id=domain_class_id,
                range_class_id=range_class_id,
                range_datatype=range_datatype,
                status=item.get("status", "imported"),
                confidence=item.get("confidence"),
            )
            db.add(property_obj)
            created_properties.append(property_obj)
            existing_properties[name.lower()] = property_obj
        else:
            property_obj.label = item.get("label", property_obj.label)
            property_obj.description = item.get("description", property_obj.description)
            property_obj.property_type = property_type
            property_obj.domain_class_id = domain_class_id if domain_name else property_obj.domain_class_id
            property_obj.range_class_id = range_class_id if range_name and property_type == "object" else property_obj.range_class_id
            property_obj.range_datatype = range_datatype if range_datatype is not None else property_obj.range_datatype
            property_obj.status = item.get("status", property_obj.status)
            property_obj.confidence = item.get("confidence", property_obj.confidence)
            updated_properties.append(property_obj)

        if property_type == "data" and not (property_obj.range_datatype or range_datatype):
            raise OntologyImportError(
                f"Data property '{name}' requires 'range_datatype'."
            )

    db.commit()

    return {
        "created_classes": created_classes,
        "updated_classes": updated_classes,
        "created_properties": created_properties,
        "updated_properties": updated_properties,
    }
