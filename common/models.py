from pydantic import BaseModel, Field
from enum import Enum
from typing import Annotated, Literal, Optional, Union


# ========== Location ==========
class LocationTypeEnum(str, Enum):
    pdf_quadpoints = "pdf_quadpoints"
    ir_anchor = "ir_anchor"


class LocationAnchor(BaseModel):
    page_num: int
    bounding_box: list[float]
    source_text: Optional[str] = None


class Location(BaseModel):
    type: LocationTypeEnum = LocationTypeEnum.pdf_quadpoints
    source_sentence: Optional[str] = None
    page_num: Optional[int] = None
    bounding_box: Optional[list[float]] = None
    para_index: Optional[int] = None
    anchors: Optional[list[LocationAnchor]] = None
    node_id: Optional[str] = None
    path: Optional[list[str]] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


# ========== Issue Types ==========
class IssueType(str, Enum):
    GrammarSpelling = 'Grammar & Spelling'
    DefinitiveLanguage = 'Definitive Language'


# ========== Risk Level ==========
class RiskLevel(str, Enum):
    high = '高'
    medium = '中'
    low = '低'


# ========== Rule Status ==========
class RuleStatusEnum(str, Enum):
    active = 'active'
    inactive = 'inactive'


# ========== Rule Type (适用/排除) ==========
class RuleTypeEnum(str, Enum):
    applicable = 'applicable'  # 适用规则
    exclusion = 'exclusion'    # 排除规则


# ========== Rule Source (内置/自定义) ==========
class RuleSourceEnum(str, Enum):
    builtin = 'builtin'   # 内置规则库
    custom = 'custom'     # 自定义规则库


# ========== Document Type ==========
class DocumentType(BaseModel):
    id: str
    name: str  # 法律合同、医学文书、财务发票、媒体文案、投标文件


# ========== Document Subtype ==========
class DocumentSubtype(BaseModel):
    id: str
    type_id: str  # 关联到 DocumentType
    name: str  # 劳动合同、租赁合同等


# ========== Rule-Subtype Relation ==========
class RuleSubtypeRelation(BaseModel):
    rule_id: str
    subtype_id: str


# ========== Rule Example ==========
class RuleExample(BaseModel):
    text: str
    explanation: str


# ========== Review Rule ==========
class ReviewRule(BaseModel):
    id: str
    name: str
    description: str
    risk_level: RiskLevel
    examples: list[RuleExample] = []
    rule_type: RuleTypeEnum = RuleTypeEnum.applicable  # 规则类型：适用/排除
    source: RuleSourceEnum = RuleSourceEnum.custom     # 规则来源：内置/自定义
    status: RuleStatusEnum = RuleStatusEnum.active
    is_universal: bool = False
    created_at: str
    updated_at: Optional[str] = None
    type_ids: list[str] = []
    subtype_ids: list[str] = []

    class Config:
        use_enum_values = True


# ========== Document (文书元数据) ==========
class Document(BaseModel):
    id: str
    owner_id: str
    original_filename: str
    display_name: str
    subtype_id: str
    storage_provider: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at_utc: str
    created_by: str
    last_run_id: Optional[str] = None
    review_status: Optional[str] = None
    review_error_message: Optional[str] = None


class SingleShotIssue(BaseModel):
    type: IssueType
    location: Location
    text: str
    explanation: str
    suggested_fix: str
    comment_id: str


class ConsolidatorIssue(BaseModel):
    comment_id: str
    score: int
    suggested_action: str
    reason_for_suggested_action: str


class CombinedIssue(SingleShotIssue, ConsolidatorIssue):
    pass


class AllSingleShotIssues(BaseModel):
    issues: list[SingleShotIssue]


class AllConsolidatorIssues(BaseModel):
    issues: list[ConsolidatorIssue]


class AllCombinedIssues(BaseModel):
    issues: list[CombinedIssue]


class BaseIssue(BaseModel):
    type: IssueType
    location: Location
    text: str
    explanation: str
    suggested_fix: str


class FlowOutputChunk(BaseModel):
    issues: list[BaseIssue]


class IssueStatusEnum(str, Enum):
    accepted = 'accepted'
    dismissed = 'dismissed'
    not_reviewed = 'not_reviewed'


class ModifiedFieldsModel(BaseModel):
    suggested_fix: Optional[str] = None
    explanation: Optional[str] = None


class DismissalFeedbackModel(BaseModel):
    reason: Optional[str] = None


class Issue(BaseModel):
    id: str
    doc_id: str
    owner_id: str = ""
    source_run_id: str = ""
    source_issue_id: Optional[str] = None
    text: str
    type: str  # IssueType value or custom rule name
    status: IssueStatusEnum
    suggested_fix: str
    explanation: str
    risk_level: Optional[RiskLevel] = None  # 风险等级：高/中/低
    location: Optional[Location] = None
    review_initiated_by: str
    review_initiated_at_UTC: str
    resolved_by: Optional[str] = None
    resolved_at_UTC: Optional[str] = None
    modified_fields: Optional[ModifiedFieldsModel] = None
    dismissal_feedback: Optional[DismissalFeedbackModel] = None
    feedback: Optional[dict] = None

    class Config:
        use_enum_values = True


# ========== Document IR ==========
class IRTextRun(BaseModel):
    id: str
    text: str


class IRParagraph(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    id: str
    runs: list[IRTextRun] = []


class IRTableCell(BaseModel):
    id: str
    blocks: list[IRParagraph] = []


class IRTableRow(BaseModel):
    id: str
    cells: list[IRTableCell] = []


class IRTable(BaseModel):
    type: Literal["table"] = "table"
    id: str
    rows: list[IRTableRow] = []


IRBlock = Annotated[Union[IRParagraph, IRTable], Field(discriminator="type")]


class DocumentIR(BaseModel):
    version: str = "ir:v1"
    blocks: list[IRBlock] = []


class IRPatchOp(BaseModel):
    op: Literal["replace"] = "replace"
    node_id: str
    start_offset: int
    end_offset: int
    text: str


class IRPatch(BaseModel):
    version: str = "irpatch:v1"
    ops: list[IRPatchOp] = []
