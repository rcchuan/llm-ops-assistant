from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DifyDatasetDocumentResult:
    document_id: str
