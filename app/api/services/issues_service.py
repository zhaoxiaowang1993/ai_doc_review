from common.logger import get_logger
from datetime import datetime, timezone
import json
from typing import AsyncGenerator, List, Optional
from uuid import uuid4

from common.models import Issue, IssueStatusEnum, ModifiedFieldsModel, DismissalFeedbackModel, ReviewRule
from database.analysis_issues_repository import AnalysisIssuesRepository
from database.analysis_runs_repository import AnalysisRunsRepository
from database.documents_repository import DocumentsRepository
from database.issues_repository import IssuesRepository
from security.auth import User
from services.lc_pipeline import LangChainPipeline
from services.hitl_agent import HitlIssuesAgent

logging = get_logger(__name__)


class IssuesService:
    def __init__(
        self,
        issues_repository: IssuesRepository,
        analysis_runs_repository: AnalysisRunsRepository,
        analysis_issues_repository: AnalysisIssuesRepository,
        documents_repository: DocumentsRepository,
        pipeline: LangChainPipeline,
    ) -> None:
        self.pipeline = pipeline
        self.issues_repository = issues_repository
        self.analysis_runs_repository = analysis_runs_repository
        self.analysis_issues_repository = analysis_issues_repository
        self.documents_repository = documents_repository
        self.hitl = (
            HitlIssuesAgent(model=self.pipeline.llm, issues_repository=self.issues_repository)
            if hasattr(self.pipeline, "llm")
            else None
        )

    async def get_issues_data(self, doc_id: str, *, owner_id: str) -> List[Issue]:
        try:
            logging.debug(f"Retrieving document issues for {doc_id}")
            issues = await self.issues_repository.get_issues(doc_id, owner_id=owner_id)
            return issues
        except Exception as e:
            logging.error(f"Error retrieving PDF issues for doc_id={doc_id}: {str(e)}")
            raise e

    async def clone_issues_from_analysis_run(
        self,
        *,
        document_id: str,
        owner_id: str,
        run_id: str,
        review_initiated_by: str,
        review_initiated_at_utc: str,
    ) -> List[Issue]:
        canonical = await self.analysis_issues_repository.list_by_run_id(run_id, owner_id=owner_id)
        issues: List[Issue] = []
        for c in canonical:
            location = None
            try:
                raw = c.get("location_json")
                location = json.loads(raw) if raw else None
            except Exception:
                location = None

            issues.append(
                Issue(
                    id=str(uuid4()),
                    doc_id=document_id,
                    owner_id=owner_id,
                    source_run_id=run_id,
                    source_issue_id=c.get("id"),
                    text=c.get("text") or "",
                    type=c.get("type") or "",
                    status=IssueStatusEnum.not_reviewed,
                    suggested_fix=c.get("suggested_fix") or "",
                    explanation=c.get("explanation") or "",
                    risk_level=c.get("risk_level"),
                    location=location,
                    review_initiated_by=review_initiated_by,
                    review_initiated_at_UTC=review_initiated_at_utc,
                )
            )

        await self.issues_repository.store_issues(issues)
        return issues

    async def initiate_review(
        self,
        *,
        document_id: str,
        owner_id: str,
        subtype_id: str,
        pdf_path: str,
        user: User,
        time_stamp: datetime | str,
        rules_snapshot_json: str,
        rules_fingerprint: str,
        pipeline_version: str,
        mineru_cache_key: str,
        force: bool = False,
        custom_rules: List[ReviewRule] | None = None,
    ) -> AsyncGenerator[List[Issue], None]:
        run_id: Optional[str] = None
        try:
            timestamp_iso = time_stamp.isoformat() if isinstance(time_stamp, datetime) else str(time_stamp)
            cached: Optional[dict] = None
            if not force:
                existing = await self.issues_repository.get_issues(document_id, owner_id=owner_id)
                if existing:
                    yield existing
                    return

                cached = await self.analysis_runs_repository.get_by_key(
                    owner_id=owner_id,
                    sha256=mineru_cache_key,
                    rules_fingerprint=rules_fingerprint,
                    pipeline_version=pipeline_version,
                )
                if cached and (cached.get("status") == "completed"):
                    await self.documents_repository.update_last_run_id(
                        document_id, owner_id=owner_id, last_run_id=cached["id"]
                    )
                    cloned = await self.clone_issues_from_analysis_run(
                        document_id=document_id,
                        owner_id=owner_id,
                        run_id=cached["id"],
                        review_initiated_by=user.oid,
                        review_initiated_at_utc=timestamp_iso,
                    )
                    yield cloned
                    return

            if cached and cached.get("status") != "completed":
                run_id = cached["id"]
                await self.analysis_runs_repository.update(
                    run_id,
                    owner_id=owner_id,
                    fields={
                        "subtype_id": subtype_id,
                        "rules_snapshot_json": rules_snapshot_json,
                        "created_at_utc": timestamp_iso,
                        "status": "running",
                        "error_message": None,
                    },
                )
            else:
                run_id = str(uuid4())
                await self.analysis_runs_repository.create(
                    {
                        "id": run_id,
                        "owner_id": owner_id,
                        "sha256": mineru_cache_key,
                        "subtype_id": subtype_id,
                        "rules_fingerprint": rules_fingerprint,
                        "rules_snapshot_json": rules_snapshot_json,
                        "pipeline_version": pipeline_version,
                        "mineru_cache_key": mineru_cache_key,
                        "created_at_utc": timestamp_iso,
                        "status": "running",
                        "error_message": None,
                    }
                )
            await self.documents_repository.update_last_run_id(document_id, owner_id=owner_id, last_run_id=run_id)

            stream_data = self.pipeline.stream_issues(
                doc_id=document_id,
                pdf_path=pdf_path,
                user_id=user.oid,
                timestamp_iso=timestamp_iso,
                custom_rules=custom_rules,
                cache_key=mineru_cache_key,
            )
            async for issues in stream_data:
                for issue in issues:
                    issue.owner_id = owner_id
                    issue.source_run_id = run_id
                    issue.source_issue_id = None
                await self.issues_repository.store_issues(issues)
                await self.analysis_issues_repository.store_issues(run_id, issues)
                yield issues

            await self.analysis_runs_repository.update(
                run_id,
                owner_id=owner_id,
                fields={"status": "completed"},
            )
        except Exception as e:
            logging.error(f"Error initiating review for document {pdf_path}: {str(e)}")
            try:
                if run_id:
                    await self.analysis_runs_repository.update(
                        run_id,
                        owner_id=owner_id,
                        fields={"status": "failed", "error_message": str(e)},
                    )
            except Exception:
                pass
            raise

    async def accept_issue(
        self, issue_id: str, user: User, modified_fields: ModifiedFieldsModel | None = None
    ) -> Issue:
        try:
            if self.hitl is None:
                raise RuntimeError("HITL is unavailable")
            update_fields = {
                "status": IssueStatusEnum.accepted.value,
                "resolved_by": user.oid,
                "resolved_at_UTC": datetime.now(timezone.utc).isoformat(),
            }

            if modified_fields:
                update_fields["modified_fields"] = modified_fields.model_dump(exclude_none=True)

            return await self.hitl.apply_update_with_hitl(
                thread_id=f"issue:{issue_id}:{uuid4()}",
                issue_id=issue_id,
                update_fields=update_fields,
                owner_id=user.oid,
            )
        except Exception as e:
            logging.error(f"Failed to accept issue {issue_id}: {e}")
            raise

    async def dismiss_issue(
        self, issue_id: str, user: User, dismissal_feedback: DismissalFeedbackModel | None = None
    ) -> Issue:
        try:
            if self.hitl is None:
                raise RuntimeError("HITL is unavailable")
            update_fields = {
                "status": IssueStatusEnum.dismissed.value,
                "resolved_by": user.oid,
                "resolved_at_UTC": datetime.now(timezone.utc).isoformat(),
            }

            if dismissal_feedback:
                update_fields["dismissal_feedback"] = dismissal_feedback.model_dump()

            return await self.hitl.apply_update_with_hitl(
                thread_id=f"issue:{issue_id}:{uuid4()}",
                issue_id=issue_id,
                update_fields=update_fields,
                owner_id=user.oid,
            )
        except Exception as e:
            logging.error(f"Failed to dismiss issue {issue_id}: {e}")
            raise

    async def add_feedback(
        self,
        issue_id: str,
        user: User,
        feedback: DismissalFeedbackModel | None = None,
    ) -> Issue:
        try:
            if self.hitl is None:
                raise RuntimeError("HITL is unavailable")
            if feedback is None or feedback.model_dump(exclude_none=True) == {}:
                return await self.hitl.get_issue(issue_id, owner_id=user.oid)
            return await self.hitl.apply_update_with_hitl(
                thread_id=f"issue:{issue_id}:{uuid4()}",
                issue_id=issue_id,
                update_fields={"dismissal_feedback": feedback.model_dump(exclude_none=True)},
                owner_id=user.oid,
            )
        except Exception as e:
            logging.error(f"Failed to provide feedback on issue {issue_id}: {e}")
            raise
