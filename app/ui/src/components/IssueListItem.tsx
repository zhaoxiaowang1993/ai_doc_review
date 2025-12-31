import { Badge, makeStyles, mergeClasses, tokens } from '@fluentui/react-components'
import { Circle16Filled, CheckmarkCircle16Filled, DismissCircle16Filled } from '@fluentui/react-icons'
import { issueRiskLevel, issueRiskTone, issueStatusLabel, normalizeIssueStatus, issueTypeLabel } from '../i18n/labels'
import { Issue, IssueStatus } from '../types/issue'

const useStyles = makeStyles({
  item: {
    cursor: 'pointer',
    padding: '14px',
    borderRadius: '12px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground2,
    transitionProperty: 'all',
    transitionDuration: '200ms',
    transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden',
    flexShrink: 0,
    '&:hover': {
      borderTopColor: tokens.colorNeutralStroke1,
      borderRightColor: tokens.colorNeutralStroke1,
      borderBottomColor: tokens.colorNeutralStroke1,
      borderLeftColor: tokens.colorNeutralStroke1,
      backgroundColor: tokens.colorNeutralBackground3,
      transform: 'translateX(4px)',
      boxShadow: tokens.shadow8,
    },
  },
  selected: {
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
    backgroundColor: tokens.colorBrandBackground2,
    boxShadow: tokens.shadow8,
    '&::before': {
      content: '""',
      position: 'absolute',
      left: 0,
      top: 0,
      bottom: 0,
      width: '3px',
      backgroundColor: tokens.colorBrandBackground,
    },
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    marginBottom: '10px',
  },
  statusIcon: {
    flexShrink: 0,
    marginTop: '2px',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    lineHeight: '1.4',
    color: tokens.colorNeutralForeground1,
  },
  titleDismissed: {
    textDecoration: 'line-through',
    opacity: 0.6,
  },
  meta: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  pageNum: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 8px',
    borderRadius: '4px',
    backgroundColor: tokens.colorNeutralBackground3,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    fontFamily: 'monospace',
  },
  status: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
  },
  // Status-specific styles
  accepted: {
    '& $statusIcon svg': {
      color: tokens.colorPaletteGreenForeground1,
    },
  },
  dismissed: {
    opacity: 0.7,
  },
})

export function IssueListItem({
  issue,
  selected,
  onSelect,
}: {
  issue: Issue
  selected: boolean
  onSelect: (issue: Issue) => void
}) {
  const classes = useStyles()
  const normalizedStatus = normalizeIssueStatus(issue.status as unknown as string)

  const statusIcon =
    normalizedStatus === IssueStatus.Accepted ? (
      <CheckmarkCircle16Filled primaryFill={tokens.colorPaletteGreenForeground1} />
    ) : normalizedStatus === IssueStatus.Dismissed ? (
      <DismissCircle16Filled primaryFill={tokens.colorNeutralForeground3} />
    ) : (
      <Circle16Filled primaryFill={tokens.colorBrandForeground1} />
    )

  const isDismissed = normalizedStatus === IssueStatus.Dismissed

  return (
    <div
      className={mergeClasses(
        classes.item,
        selected && classes.selected,
        isDismissed && classes.dismissed
      )}
      onClick={() => onSelect(issue)}
    >
      <div className={classes.header}>
        <span className={classes.statusIcon}>{statusIcon}</span>
        <span className={mergeClasses(classes.title, isDismissed && classes.titleDismissed)}>
          {issue.text}
        </span>
      </div>
      <div className={classes.meta}>
        <Badge appearance="tint" shape="rounded" color={issueRiskTone(issue.type, issue.risk_level)}>
          {issueRiskLevel(issue.type, issue.risk_level)}风险
        </Badge>
        <Badge appearance="outline" shape="rounded" color="informative">
          {issueTypeLabel(issue.type)}
        </Badge>
        <span className={classes.pageNum}>P{issue.location?.page_num ?? '-'}</span>
        <span className={classes.status}>{issueStatusLabel(issue.status as unknown as string)}</span>
      </div>
    </div>
  )
}
