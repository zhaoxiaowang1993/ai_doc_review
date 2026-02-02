import { Tag } from 'antd'
import { issueRiskLevel, issueRiskTone, issueStatusLabel, normalizeIssueStatus, issueTypeLabel } from '../i18n/labels'
import { Issue, IssueStatus } from '../types/issue'

export function IssueListItem({
  issue,
  selected,
  onSelect,
}: {
  issue: Issue
  selected: boolean
  onSelect: (issue: Issue) => void
}) {
  const normalizedStatus = normalizeIssueStatus(issue.status as unknown as string)

  const isDismissed = normalizedStatus === IssueStatus.Dismissed

  const riskTone = issueRiskTone(issue.type, issue.risk_level)
  const riskColor = riskTone === 'danger' ? 'error' : riskTone === 'warning' ? 'warning' : riskTone === 'success' ? 'success' : 'processing'
  const statusColor = normalizedStatus === IssueStatus.Accepted ? 'success' : normalizedStatus === IssueStatus.Dismissed ? 'default' : 'processing'

  return (
    <div
      className={`review-issue-item ${selected ? 'review-issue-item-selected' : ''}`}
      onClick={() => onSelect(issue)}
    >
      <div className={`review-issue-title ${isDismissed ? 'review-issue-title-dismissed' : ''}`}>
        {issue.text}
      </div>
      <div className="review-issue-meta">
        <span className="review-issue-status">
          <Tag color={statusColor}>{issueStatusLabel(issue.status as unknown as string)}</Tag>
        </span>
        <Tag color={riskColor}>{issueRiskLevel(issue.type, issue.risk_level)}风险</Tag>
        <Tag>{issueTypeLabel(issue.type)}</Tag>
      </div>
    </div>
  )
}
