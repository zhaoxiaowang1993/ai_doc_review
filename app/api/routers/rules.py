from http import HTTPStatus
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from common.logger import get_logger
from common.models import (
    ReviewRule, RiskLevel, RuleExample,
    RuleTypeEnum, RuleSourceEnum, DocumentType, DocumentSubtype
)
from services.rules_service import RulesService, RuleValidationError
from dependencies import get_rules_service

router = APIRouter()
logging = get_logger(__name__)


# ========== Request/Response Models ==========

class CreateRuleRequest(BaseModel):
    name: str
    description: str
    risk_level: RiskLevel
    examples: Optional[List[RuleExample]] = None
    rule_type: RuleTypeEnum = RuleTypeEnum.applicable
    source: RuleSourceEnum = RuleSourceEnum.custom
    is_universal: Optional[bool] = None
    type_ids: Optional[List[str]] = None
    subtype_ids: Optional[List[str]] = None


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    examples: Optional[List[RuleExample]] = None
    rule_type: Optional[RuleTypeEnum] = None
    source: Optional[RuleSourceEnum] = None
    status: Optional[str] = None
    is_universal: Optional[bool] = None
    type_ids: Optional[List[str]] = None
    subtype_ids: Optional[List[str]] = None


class CreateSubtypeRequest(BaseModel):
    id: str
    type_id: str
    name: str


class DocumentTypeWithSubtypes(BaseModel):
    id: str
    name: str
    subtypes: List[DocumentSubtype]


# ========== Rules CRUD Endpoints ==========

@router.get(
    "/api/v1/rules",
    summary="Get all review rules",
    response_model=List[ReviewRule],
    responses={
        HTTPStatus.OK: {"description": "Rules retrieved successfully"},
    },
)
async def get_rules(
    rules_service: RulesService = Depends(get_rules_service),
) -> List[ReviewRule]:
    """Get all review rules."""
    logging.info("Retrieving all rules")
    return await rules_service.get_all_rules()


@router.post(
    "/api/v1/rules",
    summary="Create a new review rule",
    response_model=ReviewRule,
    responses={
        HTTPStatus.OK: {"description": "Rule created successfully"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid data provided"},
    },
)
async def create_rule(
    body: CreateRuleRequest,
    rules_service: RulesService = Depends(get_rules_service),
) -> ReviewRule:
    """Create a new review rule."""
    logging.info(f"Creating rule: {body.name}")
    try:
        return await rules_service.create_rule(
            name=body.name,
            description=body.description,
            risk_level=body.risk_level,
            examples=body.examples,
            rule_type=body.rule_type,
            source=body.source,
            is_universal=body.is_universal,
            type_ids=body.type_ids,
            subtype_ids=body.subtype_ids,
        )
    except RuleValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/api/v1/rules/{rule_id}",
    summary="Get a specific rule",
    response_model=ReviewRule,
    responses={
        HTTPStatus.OK: {"description": "Rule retrieved successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
    },
)
async def get_rule(
    rule_id: str,
    rules_service: RulesService = Depends(get_rules_service),
) -> ReviewRule:
    """Get a specific rule by ID."""
    try:
        return await rules_service.get_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/api/v1/rules/{rule_id}",
    summary="Update a rule",
    response_model=ReviewRule,
    responses={
        HTTPStatus.OK: {"description": "Rule updated successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
    },
)
async def update_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    rules_service: RulesService = Depends(get_rules_service),
) -> ReviewRule:
    """Update a rule."""
    try:
        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        return await rules_service.update_rule(rule_id, fields)
    except RuleValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/api/v1/rules/{rule_id}",
    summary="Delete a rule",
    responses={
        HTTPStatus.OK: {"description": "Rule deleted successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
    },
)
async def delete_rule(
    rule_id: str,
    rules_service: RulesService = Depends(get_rules_service),
) -> dict:
    """Delete a rule."""
    try:
        await rules_service.delete_rule(rule_id)
        return {"message": "Rule deleted", "rule_id": rule_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== Document Types Endpoints ==========

@router.get(
    "/api/v1/document-types",
    summary="Get all document types with their subtypes",
    response_model=List[DocumentTypeWithSubtypes],
    responses={
        HTTPStatus.OK: {"description": "Document types retrieved successfully"},
    },
)
async def get_document_types(
    rules_service: RulesService = Depends(get_rules_service),
) -> List[DocumentTypeWithSubtypes]:
    """Get all document types with their subtypes in a hierarchical structure."""
    logging.info("Retrieving all document types with subtypes")
    types = await rules_service.get_all_document_types()
    result = []
    for doc_type in types:
        if doc_type.id == "type_universal":
            continue
        subtypes = await rules_service.get_subtypes_by_type(doc_type.id)
        result.append(DocumentTypeWithSubtypes(
            id=doc_type.id,
            name=doc_type.name,
            subtypes=subtypes
        ))
    return result


@router.get(
    "/api/v1/document-types/{type_id}/subtypes",
    summary="Get subtypes for a specific document type",
    response_model=List[DocumentSubtype],
    responses={
        HTTPStatus.OK: {"description": "Subtypes retrieved successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Document type not found"},
    },
)
async def get_subtypes_by_type(
    type_id: str,
    rules_service: RulesService = Depends(get_rules_service),
) -> List[DocumentSubtype]:
    """Get all subtypes for a specific document type."""
    doc_type = await rules_service.get_document_type(type_id)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type {type_id} not found")
    return await rules_service.get_subtypes_by_type(type_id)


@router.post(
    "/api/v1/document-subtypes",
    summary="Create a new document subtype",
    response_model=DocumentSubtype,
    responses={
        HTTPStatus.OK: {"description": "Subtype created successfully"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid data provided"},
    },
)
async def create_document_subtype(
    body: CreateSubtypeRequest,
    rules_service: RulesService = Depends(get_rules_service),
) -> DocumentSubtype:
    """Create a new document subtype."""
    logging.info(f"Creating subtype: {body.name} under type {body.type_id}")
    subtype = DocumentSubtype(id=body.id, type_id=body.type_id, name=body.name)
    return await rules_service.create_document_subtype(subtype)


@router.delete(
    "/api/v1/document-subtypes/{subtype_id}",
    summary="Delete a document subtype",
    responses={
        HTTPStatus.OK: {"description": "Subtype deleted successfully"},
    },
)
async def delete_document_subtype(
    subtype_id: str,
    rules_service: RulesService = Depends(get_rules_service),
) -> dict:
    """Delete a document subtype."""
    await rules_service.delete_document_subtype(subtype_id)
    return {"message": "Subtype deleted", "subtype_id": subtype_id}


# ========== Rules by Subtype Endpoints ==========

@router.get(
    "/api/v1/rules/by-subtype/{subtype_id}",
    summary="Get rules associated with a document subtype",
    response_model=List[ReviewRule],
    responses={
        HTTPStatus.OK: {"description": "Rules retrieved successfully"},
    },
)
async def get_rules_by_subtype(
    subtype_id: str,
    include_universal: bool = Query(True, description="Include universal rules"),
    rules_service: RulesService = Depends(get_rules_service),
) -> List[ReviewRule]:
    """Get all active rules associated with a specific document subtype."""
    logging.info(f"Retrieving rules for subtype {subtype_id}")
    return await rules_service.get_rules_by_subtype(subtype_id, include_universal)


@router.get(
    "/api/v1/rules/for-review/{subtype_id}",
    summary="Get rules for document review (multi-level loading)",
    response_model=List[ReviewRule],
    responses={
        HTTPStatus.OK: {"description": "Rules retrieved successfully"},
    },
)
async def get_rules_for_review(
    subtype_id: str,
    rules_service: RulesService = Depends(get_rules_service),
) -> List[ReviewRule]:
    """
    获取审核文书时需要加载的规则，支持多级继承：
    1. 加载关联了当前子类的规则
    2. 加载关联了当前子类所属父类的规则
    3. 加载关联了 'universal' 的通用规则
    """
    logging.info(f"Getting rules for review with subtype {subtype_id}")
    return await rules_service.get_rules_for_review(subtype_id)

