from collections.abc import Iterable
from io import BytesIO
import json
import re

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "item"


def _datatype_uri(name: str | None) -> URIRef:
    mapping = {
        "string": XSD.string,
        "integer": XSD.integer,
        "int": XSD.integer,
        "decimal": XSD.decimal,
        "float": XSD.float,
        "double": XSD.double,
        "boolean": XSD.boolean,
        "date": XSD.date,
        "datetime": XSD.dateTime,
    }
    return mapping.get((name or "string").lower(), XSD.string)


def _literal_from_value(value: str, datatype_name: str | None) -> Literal:
    datatype = _datatype_uri(datatype_name)
    return Literal(value, datatype=datatype)


def build_project_rdf_graph(project: Project, db: Session) -> Graph:
    graph = Graph()
    base = Namespace(f"https://ontoforge.local/project/{project.id}/")
    schema_ns = Namespace(str(base) + "schema/")
    entity_ns = Namespace(str(base) + "entity/")
    relation_ns = Namespace(str(base) + "relation/")
    meta_ns = Namespace("https://ontoforge.local/meta/")

    graph.bind("of", base)
    graph.bind("ofs", schema_ns)
    graph.bind("ofe", entity_ns)
    graph.bind("ofr", relation_ns)
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)
    graph.bind("meta", meta_ns)

    ontology_uri = URIRef(str(base) + "ontology")
    graph.add((ontology_uri, RDF.type, OWL.Ontology))
    graph.add((ontology_uri, RDFS.label, Literal(project.name)))
    if project.description:
        graph.add((ontology_uri, RDFS.comment, Literal(project.description)))

    classes = list(db.scalars(select(OntologyClass).where(OntologyClass.project_id == project.id)).all())
    properties = list(db.scalars(select(OntologyProperty).where(OntologyProperty.project_id == project.id)).all())
    entities = list(db.scalars(select(KGEntity).where(KGEntity.project_id == project.id)).all())
    relations = list(db.scalars(select(RelationInstance).where(RelationInstance.project_id == project.id)).all())

    class_uris: dict[int, URIRef] = {}
    property_uris: dict[int, URIRef] = {}
    entity_uris: dict[int, URIRef] = {}

    for ontology_class in classes:
        class_uri = URIRef(str(schema_ns) + f"class/{ontology_class.id}-{_slug(ontology_class.name)}")
        class_uris[ontology_class.id] = class_uri
        graph.add((class_uri, RDF.type, OWL.Class))
        graph.add((class_uri, RDFS.label, Literal(ontology_class.label or ontology_class.name)))
        if ontology_class.description:
            graph.add((class_uri, RDFS.comment, Literal(ontology_class.description)))
        graph.add((class_uri, meta_ns.status, Literal(ontology_class.status)))
        graph.add((class_uri, meta_ns.source, Literal(ontology_class.source)))

    for ontology_class in classes:
        if ontology_class.parent_class_id and ontology_class.parent_class_id in class_uris:
            graph.add((class_uris[ontology_class.id], RDFS.subClassOf, class_uris[ontology_class.parent_class_id]))

    for ontology_property in properties:
        property_uri = URIRef(str(schema_ns) + f"property/{ontology_property.id}-{_slug(ontology_property.name)}")
        property_uris[ontology_property.id] = property_uri
        if ontology_property.property_type == "data":
            graph.add((property_uri, RDF.type, OWL.DatatypeProperty))
        else:
            graph.add((property_uri, RDF.type, OWL.ObjectProperty))
        graph.add((property_uri, RDFS.label, Literal(ontology_property.label or ontology_property.name)))
        if ontology_property.description:
            graph.add((property_uri, RDFS.comment, Literal(ontology_property.description)))
        if ontology_property.domain_class_id and ontology_property.domain_class_id in class_uris:
            graph.add((property_uri, RDFS.domain, class_uris[ontology_property.domain_class_id]))
        if ontology_property.property_type == "data":
            graph.add((property_uri, RDFS.range, _datatype_uri(ontology_property.range_datatype)))
        elif ontology_property.range_class_id and ontology_property.range_class_id in class_uris:
            graph.add((property_uri, RDFS.range, class_uris[ontology_property.range_class_id]))

    property_by_id = {item.id: item for item in properties}

    for entity in entities:
        entity_uri = URIRef(str(entity_ns) + f"{entity.id}-{_slug(entity.canonical_name)}")
        entity_uris[entity.id] = entity_uri
        graph.add((entity_uri, RDFS.label, Literal(entity.canonical_name)))
        graph.add((entity_uri, meta_ns.source, Literal(entity.source)))
        if entity.ontology_class_id and entity.ontology_class_id in class_uris:
            graph.add((entity_uri, RDF.type, class_uris[entity.ontology_class_id]))

    for relation in relations:
        subject_uri = entity_uris.get(relation.subject_entity_id)
        predicate_uri = property_uris.get(relation.predicate_id)
        if subject_uri is None or predicate_uri is None:
            continue

        if relation.object_entity_id and relation.object_entity_id in entity_uris:
            graph.add((subject_uri, predicate_uri, entity_uris[relation.object_entity_id]))
        elif relation.object_value is not None:
            property_obj = property_by_id.get(relation.predicate_id)
            graph.add((subject_uri, predicate_uri, _literal_from_value(relation.object_value, property_obj.range_datatype if property_obj else None)))

        relation_uri = URIRef(str(relation_ns) + str(relation.id))
        graph.add((relation_uri, RDF.type, meta_ns.RelationInstance))
        graph.add((relation_uri, meta_ns.subject, subject_uri))
        graph.add((relation_uri, meta_ns.predicate, predicate_uri))
        if relation.object_entity_id and relation.object_entity_id in entity_uris:
            graph.add((relation_uri, meta_ns.object, entity_uris[relation.object_entity_id]))
        elif relation.object_value is not None:
            property_obj = property_by_id.get(relation.predicate_id)
            graph.add((relation_uri, meta_ns.objectLiteral, _literal_from_value(relation.object_value, property_obj.range_datatype if property_obj else None)))
        if relation.evidence_text:
            graph.add((relation_uri, RDFS.comment, Literal(relation.evidence_text)))
        if relation.source_document_id is not None:
            graph.add((relation_uri, meta_ns.sourceDocumentId, Literal(relation.source_document_id)))

    return graph


def serialize_project_graph(project: Project, db: Session, format_name: str) -> tuple[bytes, str, str]:
    graph = build_project_rdf_graph(project, db)
    if format_name == "json-ld":
        data = graph.serialize(format="json-ld", indent=2)
        return data.encode("utf-8") if isinstance(data, str) else data, "application/ld+json", "jsonld"
    if format_name == "owl":
        data = graph.serialize(format="pretty-xml")
        return data.encode("utf-8") if isinstance(data, str) else data, "application/owl+xml", "owl"
    if format_name == "rdf":
        data = graph.serialize(format="pretty-xml")
        return data.encode("utf-8") if isinstance(data, str) else data, "application/rdf+xml", "rdf"
    if format_name == "turtle":
        data = graph.serialize(format="turtle")
        return data.encode("utf-8") if isinstance(data, str) else data, "text/turtle", "ttl"
    raise ValueError(f"Unsupported export format: {format_name}")
