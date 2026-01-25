import {
  Badge,
  Card,
  Checkbox,
  MessageBar,
  MessageBarBody,
  Spinner,
  makeStyles,
  tokens,
} from '@fluentui/react-components'
import { useEffect, useState } from 'react'
import {
  getRules,
  getRulesForReview,
} from '../services/api'
import type { ReviewRule } from '../types/rule'
import { RiskLevel, RuleStatus } from '../types/rule'

const useStyles = makeStyles({
  panel: {
    borderRadius: '12px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    overflow: 'visible',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 16px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  ruleList: {
    padding: '8px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  ruleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 12px',
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    transitionProperty: 'all',
    transitionDuration: '150ms',
    '&:hover': {
      backgroundColor: tokens.colorNeutralBackground2,
      borderTopColor: tokens.colorNeutralStroke1,
      borderRightColor: tokens.colorNeutralStroke1,
      borderBottomColor: tokens.colorNeutralStroke1,
      borderLeftColor: tokens.colorNeutralStroke1,
    },
  },
  ruleContent: {
    flex: 1,
    minWidth: 0,
  },
  ruleName: {
    fontSize: '13px',
    fontWeight: 500,
    color: tokens.colorNeutralForeground1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  ruleDesc: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    marginTop: '2px',
  },
  ruleActions: {
    display: 'flex',
    gap: '4px',
    opacity: 0.6,
    '&:hover': {
      opacity: 1,
    },
  },
  emptyState: {
    padding: '32px 16px',
    textAlign: 'center',
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    lineHeight: '1.6',
  },
  categoryBadge: {
    fontSize: '10px',
    marginLeft: '6px',
  },
})

const riskLevelColors: Record<RiskLevel, 'danger' | 'warning' | 'success'> = {
  [RiskLevel.High]: 'danger',
  [RiskLevel.Medium]: 'warning',
  [RiskLevel.Low]: 'success',
}

interface RulesPanelProps {
  subtypeId?: string  // 文书子类 ID，用于加载对应规则
  enabledRuleIds: string[]
  onEnabledRulesChange: (ruleIds: string[]) => void
  onRulesCountChange?: (count: number) => void
  hideHeader?: boolean
}

export function RulesPanel({ subtypeId, enabledRuleIds, onEnabledRulesChange, onRulesCountChange, hideHeader = false }: RulesPanelProps) {
  const classes = useStyles()
  const [rules, setRules] = useState<ReviewRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()

  // Load rules based on subtypeId or all rules
  useEffect(() => {
    loadData()
  }, [subtypeId])

  async function loadData() {
    setLoading(true)
    setError(undefined)
    try {
      let loadedRules: ReviewRule[]

      if (subtypeId) {
        // 如果有 subtypeId，加载对应分类的规则（多级加载）
        loadedRules = await getRulesForReview(subtypeId)
      } else {
        // 否则加载所有活动规则
        const allRules = await getRules()
        loadedRules = allRules.filter((r: ReviewRule) => r.status === RuleStatus.Active)
      }

      setRules(loadedRules)
      onRulesCountChange?.(loadedRules.length)

      // 默认启用所有加载的规则
      const enabledIds = loadedRules.map((rule: ReviewRule) => rule.id)
      onEnabledRulesChange(enabledIds)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  // 本地切换规则启用状态（不再需要调用后端）
  function handleToggleRule(ruleId: string, enabled: boolean) {
    if (enabled) {
      onEnabledRulesChange([...enabledRuleIds, ruleId])
    } else {
      onEnabledRulesChange(enabledRuleIds.filter(id => id !== ruleId))
    }
  }

  const compactRuleList = (
    <>
      {error && (
        <MessageBar intent="error" style={{ margin: '8px' }}>
          <MessageBarBody>{error}</MessageBarBody>
        </MessageBar>
      )}

      {loading ? (
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Spinner size="small" />
        </div>
      ) : (
        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {rules.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: tokens.colorNeutralForeground3, fontSize: '12px' }}>
              暂无规则
            </div>
          ) : (
            rules.map(rule => (
              <div
                key={rule.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 14px',
                  borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
                }}
              >
                <Checkbox
                  checked={enabledRuleIds.includes(rule.id)}
                  onChange={(_, data) => handleToggleRule(rule.id, !!data.checked)}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '12px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {rule.name}
                    <Badge appearance="tint" color={riskLevelColors[rule.risk_level]} size="small">
                      {rule.risk_level}
                    </Badge>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </>
  )

  return (
    <>
      {hideHeader ? compactRuleList : (
        <Card className={classes.panel}>
          <div className={classes.header}>
            <span className={classes.headerTitle}>审核规则</span>
          </div>

          {error && (
            <MessageBar intent="error" style={{ margin: '8px' }}>
              <MessageBarBody>{error}</MessageBarBody>
            </MessageBar>
          )}

          {loading ? (
            <div className={classes.emptyState}>
              <Spinner size="small" />
            </div>
          ) : rules.length === 0 ? (
            <div className={classes.emptyState}>
              暂无规则
            </div>
          ) : (
            <div className={classes.ruleList}>
              {rules.map(rule => (
                <div key={rule.id} className={classes.ruleItem}>
                  <Checkbox
                    checked={enabledRuleIds.includes(rule.id)}
                    onChange={(_, data) => handleToggleRule(rule.id, !!data.checked)}
                  />
                  <div className={classes.ruleContent}>
                    <div className={classes.ruleName}>
                      {rule.name}
                      <Badge
                        appearance="tint"
                        color={riskLevelColors[rule.risk_level]}
                        size="small"
                        style={{ marginLeft: '8px' }}
                      >
                        {rule.risk_level}
                      </Badge>
                    </div>
                    <div className={classes.ruleDesc}>{rule.description}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </>
  )
}
