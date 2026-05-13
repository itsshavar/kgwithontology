from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.models.source_document import SourceDocument
from app.services.ingestion.text_chunker import chunk_text


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        texts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                texts.append(page_text)
        return "\n\n".join(texts)
    except Exception:
        return ""


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        from docx import Document

        document = Document(BytesIO(file_bytes))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text and paragraph.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_text(filename: str, content_type: str | None, file_bytes: bytes) -> str:
    if not file_bytes:
        return ""

    lower_name = filename.lower()
    if lower_name.endswith((".txt", ".md", ".csv", ".json", ".html", ".xml", ".ttl", ".rdf", ".owl", ".n3", ".nt", ".jsonld")):
        return file_bytes.decode("utf-8", errors="ignore")

    if lower_name.endswith(".pdf") or content_type == "application/pdf":
        extracted = _extract_pdf_text(file_bytes)
        if extracted:
            return extracted

    if lower_name.endswith(".docx") or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        extracted = _extract_docx_text(file_bytes)
        if extracted:
            return extracted

    if content_type and content_type.startswith("text/"):
        return file_bytes.decode("utf-8", errors="ignore")

    return file_bytes.decode("utf-8", errors="ignore")


async def save_upload(project_id: int, upload: UploadFile) -> SourceDocument:
    project_dir = settings.upload_dir / f"project_{project_id}"
    project_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = await upload.read()
    safe_name = Path(upload.filename or "uploaded_file").name
    stored_name = f"{uuid4().hex}_{safe_name}"
    storage_path = project_dir / stored_name
    storage_path.write_bytes(file_bytes)

    raw_text = extract_text(safe_name, upload.content_type, file_bytes)
    chunks = chunk_text(raw_text)

    return SourceDocument(
        project_id=project_id,
        filename=safe_name,
        content_type=upload.content_type,
        storage_path=str(storage_path.relative_to(settings.data_dir.parent)),
        raw_text=raw_text,
        chunk_count=len(chunks),
        status="processed" if raw_text is not None else "uploaded",
    )
