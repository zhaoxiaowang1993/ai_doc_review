import os
from typing import Generator, Any
from more_itertools import batched

from azure.identity import DefaultAzureCredential
from azure.ai.formrecognizer import DocumentAnalysisClient, AnalyzeResult


DOCUMENT_INTELLIGENCE_MODEL = "prebuilt-document"
PARAGRAPHS_PER_CHUNK = 16
DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT")
STORAGE_URL_PREFIX = os.environ.get("STORAGE_URL_PREFIX")


def analyze_document(pdf_name: str) -> AnalyzeResult:
    credential = DefaultAzureCredential()
    document_analysis_client = DocumentAnalysisClient(
        endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT, credential=credential
    )

    pdf_url = f"{STORAGE_URL_PREFIX}/{pdf_name}"
    poller = document_analysis_client.begin_analyze_document_from_url(
        model_id=DOCUMENT_INTELLIGENCE_MODEL, 
        document_url=pdf_url
    )

    return poller.result()


def get_text_chunks(di_result: AnalyzeResult, paragraphs_per_chunk: int = PARAGRAPHS_PER_CHUNK) -> Generator[Any, Any, Any]:
    if paragraphs_per_chunk == -1:
        yield "\n".join([paragraph.content for paragraph in di_result.paragraphs])
    else:
        for item in map(
            lambda batch: "\n".join(batch),
            batched([f"[{i}]{paragraph.content}" for i, paragraph in enumerate(di_result.paragraphs)], paragraphs_per_chunk)):
            yield item