from pydantic import BaseModel
from enum import Enum
from typing import Optional


# ========== Location ==========
class Location(BaseModel):
    source_sentence: str
    page_num: int
    bounding_box: list[float]
    para_index: int


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
    filename: str
    subtype_id: str  # 关联到 DocumentSubtype，决定审核时加载哪些规则
    created_at: str


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

    class Config:
        use_enum_values = True
