from pydantic import BaseModel


class OntologyImportResponse(BaseModel):
    project_id: int
    imported_classes: int
    updated_classes: int
    imported_properties: int
    updated_properties: int
    message: str
