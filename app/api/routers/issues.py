from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4
from dependencies import get_documents_service, get_issues_service, get_rules_service, get_review_rule_snapshots_repository
from common.logger import get_logger
import json
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from services.documents_service import DocumentsService
from services.issues_service import IssuesService
from services.rules_service import RulesService
from fastapi.responses import StreamingResponse
from security.auth import validate_authenticated
from common.models import Issue, ModifiedFieldsModel, DismissalFeedbackModel, IssueStatusEnum
from config.config import settings
from pydantic import BaseModel
from database.review_rule_snapshots_repository import ReviewRuleSnapshotsRepository
from services.rules_fingerprint import build_review_rules_snapshot_items, compute_review_rules_fingerprint
from common.models import RiskLevel


router = APIRouter()
logging = get_logger(__name__)


def issues_event(issues: list[Issue]) -> str:
    issue_objs = [issue.model_dump() for issue in issues]
    return f"event: issues\n" + (f"data: {json.dumps(issue_objs)}\n" if issues else "") + "\n"


class HitlStartRequest(BaseModel):
    action: Literal["accept", "dismiss"]
    modified_fields: Optional[ModifiedFieldsModel] = None
    dismissal_feedback: Optional[DismissalFeedbackModel] = None


class HitlStartResponse(BaseModel):
    thread_id: str
    interrupt_id: Optional[str] = None
    proposed_action: Dict[str, Any]
    raw_interrupt: Optional[Dict[str, Any]] = None


class HitlResumeRequest(BaseModel):
    thread_id: str
    interrupt_id: Optional[str] = None
    decision: Dict[str, Any]

class ReviewRuleSnapshotItem(BaseModel):
    id: str
    name: str
    description: str
    risk_level: RiskLevel


class ReviewRulesStateResponse(BaseModel):
    snapshot_rules: List[ReviewRuleSnapshotItem]
    snapshot_reviewed_at_UTC: Optional[str] = None
    latest_rule_ids: List[str]
    rules_changed_since_review: bool


@router.get(
    "/api/v1/review/{doc_id}/rules-state",
    summary="Get review-time rules snapshot and latest rule change state",
    response_model=ReviewRulesStateResponse,
)
async def get_review_rules_state(
    doc_id: str,
    user=Depends(validate_authenticated),
    rules_service: RulesService = Depends(get_rules_service),
    documents_service: DocumentsService = Depends(get_documents_service),
    review_rule_snapshots_repository: ReviewRuleSnapshotsRepository = Depends(get_review_rule_snapshots_repository),
) -> ReviewRulesStateResponse:
    document = await documents_service.get_document(doc_id)
    subtype_id = document.subtype_id if document else None

    latest_rules = await rules_service.get_rules_for_review(subtype_id) if subtype_id else []
    latest_rule_ids = [r.id for r in latest_rules]
    latest_fingerprint = compute_review_rules_fingerprint(latest_rules)

    snapshot_row = await review_rule_snapshots_repository.get_by_doc_id(doc_id)
    if not snapshot_row:
        return ReviewRulesStateResponse(
            snapshot_rules=build_review_rules_snapshot_items(latest_rules),
            snapshot_reviewed_at_UTC=None,
            latest_rule_ids=latest_rule_ids,
            rules_changed_since_review=False,
        )

    try:
        snapshot_rules = json.loads(snapshot_row.get("rules_snapshot") or "[]")
    except Exception:
        snapshot_rules = []

    snapshot_fingerprint = snapshot_row.get("rules_fingerprint") or ""

    return ReviewRulesStateResponse(
        snapshot_rules=snapshot_rules,
        snapshot_reviewed_at_UTC=snapshot_row.get("reviewed_at_UTC"),
        latest_rule_ids=latest_rule_ids,
        rules_changed_since_review=(snapshot_fingerprint != latest_fingerprint),
    )

@router.get(
    "/api/v1/review/{doc_id}/issues",
    summary="Get issues related to a PDF document",
    responses={
        200: {"description": "Issues retrieved successfully"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_pdf_issues(
    doc_id: str,
    force: bool = Query(False, description="Force re-review even if issues exist"),
    rule_ids: Optional[List[str]] = Query(None, description="List of rule IDs to apply"),
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
    rules_service: RulesService = Depends(get_rules_service),
    documents_service: DocumentsService = Depends(get_documents_service),
    review_rule_snapshots_repository: ReviewRuleSnapshotsRepository = Depends(get_review_rule_snapshots_repository),
) -> StreamingResponse:
    """
    Retrieve issues related to the document.

    Args:
        doc_id (str): The filename of the document
        force (bool): If true, delete existing issues and re-run review
        rule_ids (List[str]): Optional list of rule IDs to use for review
        user (Depends): The authenticated user.

    Returns:
        StreamingResponse: A text events stream containing identified issues.
    """
    logging.info(f"Received initiate review request for document {doc_id}")

    try:
        stored_issues = await issues_service.get_issues_data(doc_id)

        # If force=true, delete existing issues and re-run
        if force and stored_issues:
            logging.info(f"Force re-review requested. Deleting {len(stored_issues)} existing issues for {doc_id}")
            await issues_service.issues_repository.delete_issues_by_doc(doc_id)
            stored_issues = []

        if stored_issues:
            logging.info(f"Found stored issues for document {doc_id}. Streaming issues...")

            def issues_events():
                yield issues_event(stored_issues)
                yield "event: complete\n\n"

            issues = issues_events()

        else:
            logging.info(f"No issues found for document {doc_id}. Initiating review...")
            date_time = datetime.now(timezone.utc)
            pdf_path = Path(settings.local_docs_dir) / doc_id
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="Document not found on server")

            custom_rules = None
            subtype_id: str | None = None
            if rule_ids:
                custom_rules = await rules_service.get_rules_by_ids(rule_ids)
                logging.info(f"Using {len(custom_rules)} custom rules for review")
            else:
                document = await documents_service.get_document(doc_id)
                if not document or not document.subtype_id:
                    raise HTTPException(status_code=400, detail="缺失文档分类信息，请重新上传并选择文书分类。")
                subtype_id = document.subtype_id
                custom_rules = await rules_service.get_rules_for_review(document.subtype_id)
                logging.info(f"Loaded {len(custom_rules)} rules for review (subtype_id={document.subtype_id})")

            snapshot_items = build_review_rules_snapshot_items(custom_rules or [])
            snapshot_fingerprint = compute_review_rules_fingerprint(custom_rules or [])
            await review_rule_snapshots_repository.upsert(
                doc_id=doc_id,
                reviewed_at_UTC=date_time.isoformat(),
                subtype_id=subtype_id,
                rules_snapshot=json.dumps(snapshot_items, ensure_ascii=False, separators=(",", ":")),
                rules_fingerprint=snapshot_fingerprint,
            )

            issues_stream = issues_service.initiate_review(str(pdf_path), user, date_time, custom_rules)

            async def issues_events():
                try:
                    async for issues in issues_stream:
                        yield issues_event(issues)
                    yield "event: complete\n\n"
                except Exception as e:
                    logging.error(f"Error occurred while streaming issues: {str(e)}")
                    yield "event: error\n"
                    yield f"data: {str(e)}\n\n"

            issues = issues_events()

        return StreamingResponse(issues, media_type="text/event-stream")

    except ValueError as e:
        logging.error(f"Invalid input provided for document {doc_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid input provided")
    except HTTPException as e:
        logging.error(f"HTTP Exception {e.detail}: {str(e)}")
        raise e  # Re-raise HTTP exceptions to preserve original status code and detail
    except Exception as e:
        logging.error(f"Unexpected error occurred during review request for document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch(
    "/api/v1/review/{doc_id}/issues/{issue_id}/accept",
    summary="Accept issue and optionally provide feedback",
    responses={
        HTTPStatus.OK: {"description": "Feedback updated successfully"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid data provided"},
        HTTPStatus.UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
    response_model=Issue
)
async def accept_issue(
    doc_id: str,
    issue_id: str,
    modified_fields: Optional[ModifiedFieldsModel] = None,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
) -> Issue:
    """
    Accepts specific issue within a document and adds any modified fields.

    Args:
        doc_id (str): The ID of the document.
        doc_major_version (str): The major version of the document.
        doc_minor_version (str): The minor version of the document.
        issue_id (str): The ID of the issue.
        modified_fields (ModifiedFieldsModel): The modified fields data to be updated.
        user: The authenticated user object.
        issues_service (IssuesService): The issues service instance.

    Returns:
        IssueModel: The updated issue.
    """
    logging.info(f"Request received to accept issue {issue_id} on document {doc_id}.")

    updated_issue = await issues_service.accept_issue(issue_id, user, modified_fields)

    logging.info(f"Issue {issue_id} updated successfully.")
    return updated_issue


@router.patch(
    "/api/v1/review/{doc_id}/issues/{issue_id}/dismiss",
    summary="Dismiss issue and optionally provide feedback",
    responses={
        HTTPStatus.OK: {"description": "Issue updated successfully"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid data provided"},
        HTTPStatus.UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
    response_model=Issue
)
async def dismiss_issue(
    doc_id: str,
    issue_id: str,
    dismissal_feedback: Optional[DismissalFeedbackModel] = None,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
) -> Issue:
    """
    Dismiss specific issue within a document.

    Args:
        doc_id (str): The ID of the document.
        doc_major_version (str): The major version of the document.
        doc_minor_version (str): The minor version of the document.
        issue_id (str): The ID of the issue.
        dismissal_feedback (DismissalFeedbackModel): The feedback data to be updated.
        user: The authenticated user object.
        issues_service (IssuesService): The issues service instance.

    Returns:
        IssueModel: The updated issue.
    """
    logging.info(f"Request received to dismiss issue {issue_id} on document {doc_id}.")

    updated_issue = await issues_service.dismiss_issue(issue_id, user, dismissal_feedback)

    logging.info(f"Issue {issue_id} updated successfully.")
    return updated_issue


@router.patch(
    "/api/v1/review/{doc_id}/issues/{issue_id}/feedback",
    summary="Provide feedback on a dismissed issue",
    responses={
        HTTPStatus.OK: {"description": "Issue updated successfully"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid data provided"},
        HTTPStatus.UNPROCESSABLE_ENTITY: {"description": "Validation error"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
    response_model=Issue
)
async def provide_feedback(
    doc_id: str,
    issue_id: str,
    dismissal_feedback: DismissalFeedbackModel,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
) -> Issue:
    """
    Dismiss specific issue within a document and adds feedback.
    Args:
        doc_id (str): The ID of the document.
        doc_major_version (str): The major version of the document.
        doc_minor_version (str): The minor version of the document.
        issue_id (str): The ID of the issue.
        dismissal_feedback (DismissalFeedbackModel): The feedback data to be updated.
        user: The authenticated user object.
        issues_service (IssuesService): The issues service instance.
    Returns:
        IssueModel: The updated issue.
    """
    logging.info(f"Request received to provide feedback on issue {issue_id} on document {doc_id}.")
    updated_issue = await issues_service.add_feedback(issue_id, dismissal_feedback)
    logging.info(f"Issue {issue_id} updated successfully.")
    return updated_issue


@router.post(
    "/api/v1/review/{doc_id}/issues/{issue_id}/hitl/start",
    summary="Start a HITL-gated issue update (accept/dismiss)",
    response_model=HitlStartResponse,
)
async def start_issue_hitl(
    doc_id: str,
    issue_id: str,
    body: HitlStartRequest,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
) -> HitlStartResponse:
    del doc_id  # issue_id is globally unique in our DB

    # NOTE:
    # -----
    # Originally this endpoint attempted to start a LangGraph+HITL run and required
    # an interrupt to be produced, otherwise it raised a 500 error:
    # "HITL 未产生中断，无法进入人工决策流程。"
    #
    # In practice, some runtime / version combinations may execute the tool
    # synchronously without producing an interrupt, which caused the manual-review
    # (HITL) button in the UI to fail with 500.
    #
    # For the current product UX we only need this endpoint to:
    #   1) Build the canonical update_fields payload on the server
    #   2) Return a preview/proposed action for the confirmation dialog
    # The actual update is still applied via the existing accept/dismiss APIs.
    #
    # Therefore we intentionally DO NOT start the LangGraph HITL run here anymore,
    # and we no longer require an interrupt to exist. This makes the endpoint
    # stable and avoids unnecessary Internal Server Error responses.

    update_fields: Dict[str, Any] = {
        "resolved_by": user.oid,
        "resolved_at_UTC": datetime.now(timezone.utc).isoformat(),
    }
    if body.action == "accept":
        update_fields["status"] = IssueStatusEnum.accepted.value
        if body.modified_fields:
            update_fields["modified_fields"] = body.modified_fields.model_dump(exclude_none=True)
    else:
        update_fields["status"] = IssueStatusEnum.dismissed.value
        if body.dismissal_feedback:
            update_fields["dismissal_feedback"] = body.dismissal_feedback.model_dump(exclude_none=True)

    # We still return a synthetic thread_id so that the UI has a stable identifier
    # to display / log if needed. Since we are not starting a HITL run here,
    # interrupt_id and raw_interrupt are always None.
    thread_id = f"preview:{issue_id}:{uuid4()}"
    proposed_action = {"name": "update_issue", "args": {"issue_id": issue_id, "update_fields": update_fields}}
    return HitlStartResponse(
        thread_id=thread_id,
        interrupt_id=None,
        proposed_action=proposed_action,
        raw_interrupt=None,
    )


@router.post(
    "/api/v1/review/{doc_id}/issues/{issue_id}/hitl/resume",
    summary="Resume a HITL-gated issue update with approve/edit/reject decision",
    response_model=Issue,
)
async def resume_issue_hitl(
    doc_id: str,
    issue_id: str,
    body: HitlResumeRequest,
    user=Depends(validate_authenticated),
    issues_service: IssuesService = Depends(get_issues_service),
) -> Issue:
    del doc_id
    del user

    decision = body.decision or {"type": "approve"}

    # Basic safety: enforce tool name/issue_id on edit decisions.
    if decision.get("type") == "edit":
        edited_action = decision.get("edited_action") or {}
        if edited_action.get("name") and edited_action.get("name") != "update_issue":
            raise HTTPException(status_code=400, detail="仅允许编辑 update_issue 工具调用。")
        args = edited_action.get("args") or {}
        args["issue_id"] = issue_id
        edited_action["name"] = "update_issue"
        edited_action["args"] = args
        decision["edited_action"] = edited_action

    await issues_service.hitl.resume_update(
        thread_id=body.thread_id,
        interrupt_id=body.interrupt_id,
        decision=decision,
    )
    return await issues_service.hitl.get_issue(issue_id)
