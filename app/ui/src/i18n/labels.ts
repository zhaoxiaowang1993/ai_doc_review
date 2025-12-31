export const ISSUE_TYPE_LABELS: Record<string, string> = {
  'Grammar & Spelling': '语法与拼写',
  'Definitive Language': '确定性/保证性措辞',
};

export const ISSUE_TYPE_DESCRIPTIONS: Record<string, string> = {
  'Grammar & Spelling': '拼写、语法与标点等问题（含句式结构）',
  'Definitive Language': '使用过度确定/保证性措辞（如“必须”“一定”“保证”等）',
};

export const ISSUE_STATUS_LABELS: Record<string, string> = {
  not_reviewed: '未处理',
  'not reviewed': '未处理',
  accepted: '已采纳',
  dismissed: '已驳回',
}

export type RiskLevel = '高' | '中' | '低'
export type RiskTone = 'danger' | 'warning' | 'success' | 'informative'

export const ISSUE_TYPE_RISK: Record<string, RiskLevel> = {
  'Definitive Language': '高',
  'Grammar & Spelling': '低',
}

export function issueTypeLabel(type: string): string {
  return ISSUE_TYPE_LABELS[type] ?? type;
}

export function issueTypeDescription(type: string): string | undefined {
  return ISSUE_TYPE_DESCRIPTIONS[type];
}

export function normalizeIssueStatus(status: string | undefined): string {
  if (!status) return 'not_reviewed'
  if (status === 'not reviewed') return 'not_reviewed'
  return status
}

export function issueStatusLabel(status: string | undefined): string {
  const normalized = normalizeIssueStatus(status)
  return ISSUE_STATUS_LABELS[normalized] ?? status ?? '未处理'
}

export function issueRiskLevel(type: string, issueRiskLevelValue?: string | null): RiskLevel {
  // 优先使用 issue 自身的 risk_level 字段（自定义规则会设置此值）
  if (issueRiskLevelValue) {
    // 兼容中文和英文值
    if (issueRiskLevelValue === '高' || issueRiskLevelValue === 'high') return '高'
    if (issueRiskLevelValue === '中' || issueRiskLevelValue === 'medium') return '中'
    if (issueRiskLevelValue === '低' || issueRiskLevelValue === 'low') return '低'
  }
  // 回退到基于类型的映射（预设规则）
  return ISSUE_TYPE_RISK[type] ?? '中'
}

export function issueRiskTone(type: string, issueRiskLevelValue?: string | null): RiskTone {
  const level = issueRiskLevel(type, issueRiskLevelValue)
  if (level === '高') return 'danger'
  if (level === '低') return 'success'
  return 'warning'
}
