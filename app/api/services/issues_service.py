from common.logger import get_logger
from datetime import datetime, timezone
from typing import AsyncGenerator, List
from uuid import uuid4

from common.models import Issue, IssueStatusEnum, ModifiedFieldsModel, DismissalFeedbackModel, ReviewRule
from database.issues_repository import IssuesRepository
from security.auth import User
from services.lc_pipeline import LangChainPipeline
from services.hitl_agent import HitlIssuesAgent

logging = get_logger(__name__)


class IssuesService:
    def __init__(self, issues_repository: IssuesRepository, pipeline: LangChainPipeline) -> None:
        self.pipeline = pipeline
        self.issues_repository = issues_repository
        self.hitl = HitlIssuesAgent(model=self.pipeline.llm, issues_repository=self.issues_repository)

    async def get_issues_data(self, doc_id: str) -> List[Issue]:
        try:
            logging.debug(f"Retrieving document issues for {doc_id}")
            issues = await self.issues_repository.get_issues(doc_id)
            return issues
        except Exception as e:
            logging.error(f"Error retrieving PDF issues for doc_id={doc_id}: {str(e)}")
            raise e

    async def initiate_review(
        self,
        pdf_path: str,
        user: User,
        time_stamp: datetime | str,
        custom_rules: List[ReviewRule] | None = None,
    ) -> AsyncGenerator[List[Issue], None]:
        try:
            logging.info(f"Initiating review for document {pdf_path}")
            timestamp_iso = time_stamp.isoformat() if isinstance(time_stamp, datetime) else str(time_stamp)
            stream_data = self.pipeline.stream_issues(pdf_path, user.oid, timestamp_iso, custom_rules)
            async for issues in stream_data:
                await self.issues_repository.store_issues(issues)
                yield issues
        except Exception as e:
            logging.error(f"Error initiating review for document {pdf_path}: {str(e)}")
            raise

    async def accept_issue(
        self, issue_id: str, user: User, modified_fields: ModifiedFieldsModel | None = None
    ) -> Issue:
        try:
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
            )
        except Exception as e:
            logging.error(f"Failed to accept issue {issue_id}: {e}")
            raise

    async def dismiss_issue(
        self, issue_id: str, user: User, dismissal_feedback: DismissalFeedbackModel | None = None
    ) -> Issue:
        try:
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
            )
        except Exception as e:
            logging.error(f"Failed to dismiss issue {issue_id}: {e}")
            raise

    async def add_feedback(self, issue_id: str, feedback: DismissalFeedbackModel) -> Issue:
        try:
            return await self.hitl.apply_update_with_hitl(
                thread_id=f"issue:{issue_id}:{uuid4()}",
                issue_id=issue_id,
                update_fields={"dismissal_feedback": feedback.model_dump(exclude_none=True)},
            )
        except Exception as e:
            logging.error(f"Failed to provide feedback on issue {issue_id}: {e}")
            raise
