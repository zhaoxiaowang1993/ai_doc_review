import asyncio

from services.issues_service import IssuesService
from services.rules_service import RulesService
from services.documents_service import DocumentsService
from services.lc_pipeline import LangChainPipeline
from services.storage_provider import LocalStorageProvider
from database.db_client import SQLiteClient
from database.analysis_issues_repository import AnalysisIssuesRepository
from database.analysis_runs_repository import AnalysisRunsRepository
from database.issues_repository import IssuesRepository
from database.rules_repository import RulesRepository
from database.documents_repository import DocumentsRepository


_issues_service: IssuesService | None = None
_issues_service_lock = asyncio.Lock()

_rules_service: RulesService | None = None
_rules_service_lock = asyncio.Lock()

_documents_service: DocumentsService | None = None
_documents_service_lock = asyncio.Lock()

_storage_provider: LocalStorageProvider | None = None
_storage_provider_lock = asyncio.Lock()


async def get_issues_service() -> IssuesService:
    """
    Dependency that returns a singleton IssuesService.

    HITL uses an in-memory checkpointer keyed by thread_id. If we construct a new
    service/agent on every request, multi-step HITL (start -> resume) cannot work.
    """
    global _issues_service

    if _issues_service is not None:
        return _issues_service

    async with _issues_service_lock:
        if _issues_service is not None:
            return _issues_service

        db_client = SQLiteClient()
        issues_repo = IssuesRepository(db_client)
        analysis_runs_repo = AnalysisRunsRepository(db_client)
        analysis_issues_repo = AnalysisIssuesRepository(db_client)
        documents_repo = DocumentsRepository(db_client)
        await issues_repo.init()
        await analysis_runs_repo.init()
        await analysis_issues_repo.init()
        await documents_repo.init()
        pipeline = LangChainPipeline()
        _issues_service = IssuesService(issues_repo, analysis_runs_repo, analysis_issues_repo, documents_repo, pipeline)
        return _issues_service


async def get_rules_service() -> RulesService:
    """
    Dependency that returns a singleton RulesService.
    """
    global _rules_service

    if _rules_service is not None:
        return _rules_service

    async with _rules_service_lock:
        if _rules_service is not None:
            return _rules_service

        db_client = SQLiteClient()
        repo = RulesRepository(db_client)
        await repo.init()
        _rules_service = RulesService(repo)
        return _rules_service


async def get_documents_service() -> DocumentsService:
    """
    Dependency that returns a singleton DocumentsService.
    """
    global _documents_service

    if _documents_service is not None:
        return _documents_service

    async with _documents_service_lock:
        if _documents_service is not None:
            return _documents_service

        db_client = SQLiteClient()
        repo = DocumentsRepository(db_client)
        await repo.init()
        _documents_service = DocumentsService(repo)
        return _documents_service


async def get_storage_provider() -> LocalStorageProvider:
    global _storage_provider

    if _storage_provider is not None:
        return _storage_provider

    async with _storage_provider_lock:
        if _storage_provider is not None:
            return _storage_provider

        _storage_provider = LocalStorageProvider()
        return _storage_provider

