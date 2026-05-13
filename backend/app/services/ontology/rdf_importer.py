from typing import Any
from urllib.parse import urlparse

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from app.services.ontology.importer import OntologyImportError

FORMAT_BY_SUFFIX = {
    ".ttl": "turtle",
    ".rdf": "xml",
    ".owl": "xml",
    ".xml": "xml",
    ".nt": "nt",
    ".n3": "n3",
    ".jsonld": "json-ld",
    ".json": "json-ld",
}

CONTENT_TYPE_FORMATS = {
    "text/turtle": "turtle",
    "application/x-turtle": "turtle",
    "application/rdf+xml": "xml",
    "application/owl+xml": "xml",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/n-triples": "nt",
    "text/n3": "n3",
    "application/ld+json": "json-ld",
}


def _suffix(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.lower().rsplit(".", 1)[-1]


def _local_name(value: URIRef | str) -> str:
    raw = str(value)
    parsed = urlparse(raw)
    if parsed.fragment:
        return parsed.fragment
    if parsed.path and "/" in parsed.path:
        tail = parsed.path.rstrip("/").split("/")[-1]
        if tail:
            return tail
    return raw.rsplit(":", 1)[-1]


def _label_for_resource(graph: Graph, resource: URIRef) -> str | None:
    for label in graph.objects(resource, RDFS.label):
        if isinstance(label, Literal):
            text = str(label).strip()
            if text:
                return text
    return None


def _comment_for_resource(graph: Graph, resource: URIRef) -> str | None:
    for comment in graph.objects(resource, RDFS.comment):
        if isinstance(comment, Literal):
            text = str(comment).strip()
            if text:
                return text
    return None


def _resource_name(graph: Graph, resource: URIRef) -> str:
    label = _label_for_resource(graph, resource)
    if label:
        return label
    local_name = _local_name(resource)
    if local_name:
        return local_name
    try:
        return graph.namespace_manager.normalizeUri(resource)
    except Exception:
        return str(resource)


def _is_datatype(resource: Any) -> bool:
    if not isinstance(resource, URIRef):
        return False
    if str(resource).startswith(str(XSD)):
        return True
    return resource in {
        RDFS.Literal,
        XSD.string,
        XSD.integer,
        XSD.decimal,
        XSD.float,
        XSD.double,
        XSD.boolean,
        XSD.date,
        XSD.dateTime,
    }


def _datatype_name(resource: URIRef) -> str:
    local = _local_name(resource)
    return local or "string"


def _build_payload_from_graph(graph: Graph) -> dict[str, list[dict[str, Any]]]:
    class_resources: set[URIRef] = set()
    property_resources: set[URIRef] = set()
    parent_map: dict[URIRef, URIRef] = {}
    domain_map: dict[URIRef, URIRef] = {}
    range_class_map: dict[URIRef, URIRef] = {}
    range_datatype_map: dict[URIRef, URIRef] = {}
    property_type_map: dict[URIRef, str] = {}

    for subject in graph.subjects(RDF.type, OWL.Class):
        if isinstance(subject, URIRef):
            class_resources.add(subject)
    for subject in graph.subjects(RDF.type, RDFS.Class):
        if isinstance(subject, URIRef):
            class_resources.add(subject)

    for subject, _, parent in graph.triples((None, RDFS.subClassOf, None)):
        if isinstance(subject, URIRef):
            class_resources.add(subject)
        if isinstance(parent, URIRef) and not _is_datatype(parent):
            class_resources.add(parent)
            if isinstance(subject, URIRef):
                parent_map[subject] = parent

    for subject, _, obj in graph.triples((None, RDF.type, None)):
        if not isinstance(subject, URIRef):
            continue
        if obj in {OWL.ObjectProperty, RDF.Property}:
            property_resources.add(subject)
            property_type_map[subject] = "object"
        elif obj == OWL.DatatypeProperty:
            property_resources.add(subject)
            property_type_map[subject] = "data"

    for subject, _, domain in graph.triples((None, RDFS.domain, None)):
        if isinstance(subject, URIRef):
            property_resources.add(subject)
        if isinstance(domain, URIRef) and not _is_datatype(domain):
            class_resources.add(domain)
            if isinstance(subject, URIRef):
                domain_map[subject] = domain

    for subject, _, range_value in graph.triples((None, RDFS.range, None)):
        if isinstance(subject, URIRef):
            property_resources.add(subject)
        if isinstance(range_value, URIRef):
            if _is_datatype(range_value):
                if isinstance(subject, URIRef):
                    range_datatype_map[subject] = range_value
                    property_type_map[subject] = "data"
            else:
                class_resources.add(range_value)
                if isinstance(subject, URIRef):
                    range_class_map[subject] = range_value

    class_entries: list[dict[str, Any]] = []
    class_name_lookup: dict[URIRef, str] = {}
    for resource in sorted(class_resources, key=lambda item: _resource_name(graph, item).lower()):
        name = _resource_name(graph, resource)
        class_name_lookup[resource] = name
        entry: dict[str, Any] = {
            "name": name,
            "label": _label_for_resource(graph, resource),
            "description": _comment_for_resource(graph, resource),
            "status": "imported",
            "source": "rdf-import",
        }
        parent = parent_map.get(resource)
        if parent and parent in class_name_lookup:
            entry["parent"] = class_name_lookup[parent]
        elif parent:
            entry["parent"] = _resource_name(graph, parent)
        class_entries.append(entry)

    property_entries: list[dict[str, Any]] = []
    for resource in sorted(property_resources, key=lambda item: _resource_name(graph, item).lower()):
        property_type = property_type_map.get(resource, "object")
        entry: dict[str, Any] = {
            "name": _resource_name(graph, resource),
            "label": _label_for_resource(graph, resource),
            "description": _comment_for_resource(graph, resource),
            "property_type": property_type,
            "status": "imported",
        }
        domain = domain_map.get(resource)
        if domain:
            entry["domain"] = class_name_lookup.get(domain, _resource_name(graph, domain))
        if property_type == "data":
            datatype = range_datatype_map.get(resource)
            if datatype:
                entry["range_datatype"] = _datatype_name(datatype)
        else:
            range_class = range_class_map.get(resource)
            if range_class:
                entry["range"] = class_name_lookup.get(range_class, _resource_name(graph, range_class))
        property_entries.append(entry)

    return {"classes": class_entries, "properties": property_entries}


def parse_rdf_ontology_bytes(
    file_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    raw_text = file_bytes.decode("utf-8", errors="ignore")
    attempts: list[str] = []

    suffix = _suffix(filename)
    if suffix in FORMAT_BY_SUFFIX:
        attempts.append(FORMAT_BY_SUFFIX[suffix])
    if content_type and content_type in CONTENT_TYPE_FORMATS:
        fmt = CONTENT_TYPE_FORMATS[content_type]
        if fmt not in attempts:
            attempts.append(fmt)
    for fallback in ["turtle", "xml", "n3", "nt", "json-ld"]:
        if fallback not in attempts:
            attempts.append(fallback)

    last_error: Exception | None = None
    for rdf_format in attempts:
        graph = Graph()
        try:
            graph.parse(data=raw_text, format=rdf_format)
            payload = _build_payload_from_graph(graph)
            if not payload["classes"] and not payload["properties"]:
                raise OntologyImportError("No ontology classes or properties found in the RDF/OWL file.")
            return payload, rdf_format
        except Exception as exc:
            last_error = exc

    raise OntologyImportError(f"Unable to parse ontology file as RDF/OWL/Turtle: {last_error}")
