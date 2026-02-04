export enum RiskLevel {
  High = '高',
  Medium = '中',
  Low = '低'
}

export enum RuleStatus {
  Active = 'active',
  Inactive = 'inactive'
}

export enum RuleType {
  Applicable = 'applicable',  // 适用规则
  Exclusion = 'exclusion'     // 排除规则
}

export enum RuleSource {
  Builtin = 'builtin',   // 内置规则库
  Custom = 'custom'      // 自定义规则库
}

export interface RuleExample {
  text: string
  explanation: string
}

export interface ReviewRule {
  id: string
  name: string
  description: string
  risk_level: RiskLevel
  examples: RuleExample[]
  rule_type: RuleType
  source: RuleSource
  status: RuleStatus
  is_universal: boolean
  created_at: string
  updated_at?: string
  type_ids: string[]
  subtype_ids: string[]
}

export interface ReviewRuleSnapshotItem {
  id: string
  name: string
  description: string
  risk_level: RiskLevel
}

export interface ReviewRulesState {
  snapshot_rules: ReviewRuleSnapshotItem[]
  snapshot_reviewed_at_UTC: string | null
  latest_rule_ids: string[]
  rules_changed_since_review: boolean
}

// ========== Document (文书元数据) ==========

export interface Document {
  id: string
  owner_id: string
  original_filename: string
  display_name: string
  subtype_id: string
  storage_provider: string
  storage_key: string
  mime_type: string
  size_bytes: number
  sha256: string
  created_at_utc: string
  created_by: string
  last_run_id?: string | null
}

export interface CreateRuleRequest {
  name: string
  description: string
  risk_level: RiskLevel
  examples?: RuleExample[]
  rule_type?: RuleType
  source?: RuleSource
  is_universal?: boolean
  type_ids?: string[]
  subtype_ids?: string[]
}

export interface UpdateRuleRequest {
  name?: string
  description?: string
  risk_level?: RiskLevel
  examples?: RuleExample[]
  rule_type?: RuleType
  source?: RuleSource
  status?: RuleStatus
  is_universal?: boolean
  type_ids?: string[]
  subtype_ids?: string[]
}

// ========== Document Types ==========

export interface DocumentType {
  id: string
  name: string
}

export interface DocumentSubtype {
  id: string
  type_id: string
  name: string
}

export interface DocumentTypeWithSubtypes {
  id: string
  name: string
  subtypes: DocumentSubtype[]
}
