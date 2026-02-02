import asyncio

from services.issues_service import IssuesService
from services.rules_service import RulesService
from services.documents_service import DocumentsService
from services.lc_pipeline import LangChainPipeline
from database.db_client import SQLiteClient
from database.issues_repository import IssuesRepository
from database.rules_repository import RulesRepository
from database.documents_repository import DocumentsRepository
from database.review_rule_snapshots_repository import ReviewRuleSnapshotsRepository


_issues_service: IssuesService | None = None
_issues_service_lock = asyncio.Lock()

_rules_service: RulesService | None = None
_rules_service_lock = asyncio.Lock()

_documents_service: DocumentsService | None = None
_documents_service_lock = asyncio.Lock()

_review_rule_snapshots_repo: ReviewRuleSnapshotsRepository | None = None
_review_rule_snapshots_repo_lock = asyncio.Lock()


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
        repo = IssuesRepository(db_client)
        await repo.init()
        pipeline = LangChainPipeline()
        _issues_service = IssuesService(repo, pipeline)
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


async def get_review_rule_snapshots_repository() -> ReviewRuleSnapshotsRepository:
    global _review_rule_snapshots_repo

    if _review_rule_snapshots_repo is not None:
        return _review_rule_snapshots_repo

    async with _review_rule_snapshots_repo_lock:
        if _review_rule_snapshots_repo is not None:
            return _review_rule_snapshots_repo

        db_client = SQLiteClient()
        repo = ReviewRuleSnapshotsRepository(db_client)
        await repo.init()
        _review_rule_snapshots_repo = repo
        return _review_rule_snapshots_repo

