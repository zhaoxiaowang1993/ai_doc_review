import {
  Badge,
  Button,
  Card,
  Checkbox,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Dropdown,
  Field,
  Input,
  MessageBar,
  MessageBarBody,
  Option,
  Spinner,
  Textarea,
  makeStyles,
  tokens,
} from '@fluentui/react-components'
import { Add16Regular, Delete16Regular, Edit16Regular } from '@fluentui/react-icons'
import { useEffect, useState } from 'react'
import {
  getRules,
  createRule,
  updateRule,
  deleteRule,
  getDocumentRules,
  setDocumentRule,
} from '../services/api'
import type { ReviewRule, RuleExample, CreateRuleRequest, DocumentRuleAssociation } from '../types/rule'
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
  dialogSurface: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: '12px',
    maxWidth: '500px',
    zIndex: 1000000,
  },
  formField: {
    marginBottom: '16px',
  },
  exampleSection: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: '8px',
  },
  exampleItem: {
    display: 'flex',
    gap: '8px',
    marginBottom: '8px',
    alignItems: 'flex-start',
  },
  exampleInput: {
    flex: 1,
  },
})

const riskLevelColors: Record<RiskLevel, 'danger' | 'warning' | 'success'> = {
  [RiskLevel.High]: 'danger',
  [RiskLevel.Medium]: 'warning',
  [RiskLevel.Low]: 'success',
}

interface RulesPanelProps {
  docId: string
  enabledRuleIds: string[]
  onEnabledRulesChange: (ruleIds: string[]) => void
  onRulesCountChange?: (count: number) => void
  hideHeader?: boolean
}

export function RulesPanel({ docId, enabledRuleIds, onEnabledRulesChange, onRulesCountChange, hideHeader = false }: RulesPanelProps) {
  const classes = useStyles()
  const [rules, setRules] = useState<ReviewRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<ReviewRule | null>(null)
  const [saving, setSaving] = useState(false)
  
  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Form state
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [formRiskLevel, setFormRiskLevel] = useState<RiskLevel>(RiskLevel.Medium)
  const [formExamples, setFormExamples] = useState<RuleExample[]>([])

  // Load rules and document associations
  useEffect(() => {
    loadData()
  }, [docId])

  async function loadData() {
    setLoading(true)
    setError(undefined)
    try {
      const [allRules, docRules] = await Promise.all([
        getRules(),
        getDocumentRules(docId),
      ])
      const activeRules = allRules.filter(r => r.status === RuleStatus.Active)
      setRules(activeRules)
      onRulesCountChange?.(activeRules.length)

      // Initialize enabled rules from document associations
      const enabledIds = docRules
        .filter((a: DocumentRuleAssociation) => a.enabled)
        .map((a: DocumentRuleAssociation) => a.rule_id)
      onEnabledRulesChange(enabledIds)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleRule(ruleId: string, enabled: boolean) {
    try {
      await setDocumentRule(docId, ruleId, enabled)
      if (enabled) {
        onEnabledRulesChange([...enabledRuleIds, ruleId])
      } else {
        onEnabledRulesChange(enabledRuleIds.filter(id => id !== ruleId))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function openAddDialog() {
    setEditingRule(null)
    setFormName('')
    setFormDesc('')
    setFormRiskLevel(RiskLevel.Medium)
    setFormExamples([])
    setDialogOpen(true)
  }

  function openEditDialog(rule: ReviewRule) {
    setEditingRule(rule)
    setFormName(rule.name)
    setFormDesc(rule.description)
    setFormRiskLevel(rule.risk_level)
    setFormExamples(rule.examples || [])
    setDialogOpen(true)
  }

  async function handleSave() {
    if (!formName.trim() || !formDesc.trim()) {
      setError('请填写规则名称和描述')
      return
    }

    setSaving(true)
    setError(undefined)
    try {
      const data: CreateRuleRequest = {
        name: formName.trim(),
        description: formDesc.trim(),
        risk_level: formRiskLevel,
        examples: formExamples.filter(e => e.text.trim()),
      }

      if (editingRule) {
        await updateRule(editingRule.id, data)
      } else {
        await createRule(data)
      }

      setDialogOpen(false)
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  function openDeleteDialog(ruleId: string) {
    setDeletingRuleId(ruleId)
    setDeleteDialogOpen(true)
  }

  async function handleConfirmDelete() {
    if (!deletingRuleId) return
    setDeleting(true)
    try {
      await deleteRule(deletingRuleId)
      await loadData()
      setDeleteDialogOpen(false)
      setDeletingRuleId(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDeleting(false)
    }
  }

  function addExample() {
    setFormExamples([...formExamples, { text: '', explanation: '' }])
  }

  function updateExample(index: number, field: keyof RuleExample, value: string) {
    const updated = [...formExamples]
    updated[index] = { ...updated[index], [field]: value }
    setFormExamples(updated)
  }

  function removeExample(index: number) {
    setFormExamples(formExamples.filter((_, i) => i !== index))
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
                <div style={{ display: 'flex', gap: '2px', opacity: 0.7 }}>
                  <Button size="small" appearance="subtle" icon={<Edit16Regular />} onClick={() => openEditDialog(rule)} />
                  <Button size="small" appearance="subtle" icon={<Delete16Regular />} onClick={() => openDeleteDialog(rule.id)} />
                </div>
              </div>
            ))
          )}
          <div style={{ padding: '8px 14px', borderTop: rules.length > 0 ? 'none' : undefined }}>
            <Button size="small" appearance="subtle" icon={<Add16Regular />} onClick={openAddDialog}>
              添加规则
            </Button>
          </div>
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
            <Button
              size="small"
              appearance="subtle"
              icon={<Add16Regular />}
              onClick={openAddDialog}
            >
              添加
            </Button>
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
              暂无自定义规则，点击"添加"创建新规则
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
                  <div className={classes.ruleActions}>
                    <Button
                      size="small"
                      appearance="subtle"
                      icon={<Edit16Regular />}
                      onClick={() => openEditDialog(rule)}
                    />
                    <Button
                      size="small"
                      appearance="subtle"
                      icon={<Delete16Regular />}
                      onClick={() => openDeleteDialog(rule.id)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(_, data) => setDialogOpen(data.open)} modalType="modal">
        <DialogSurface className={classes.dialogSurface} style={{ zIndex: 1000000 }}>
          <DialogBody>
            <DialogTitle>{editingRule ? '编辑规则' : '添加规则'}</DialogTitle>
            <DialogContent>
              <Field label="规则名称" required className={classes.formField}>
                <Input
                  value={formName}
                  onChange={(_, data) => setFormName(data.value)}
                  placeholder="例如：敏感词检测"
                />
              </Field>

              <Field label="规则描述" required className={classes.formField}>
                <Textarea
                  value={formDesc}
                  onChange={(_, data) => setFormDesc(data.value)}
                  placeholder="描述该规则检测的问题类型..."
                  rows={3}
                />
              </Field>

              <Field label="风险等级" className={classes.formField}>
                <Dropdown
                  value={formRiskLevel}
                  selectedOptions={[formRiskLevel]}
                  onOptionSelect={(_, data) => setFormRiskLevel(data.optionValue as RiskLevel)}
                >
                  <Option value={RiskLevel.High}>高</Option>
                  <Option value={RiskLevel.Medium}>中</Option>
                  <Option value={RiskLevel.Low}>低</Option>
                </Dropdown>
              </Field>

              <div className={classes.exampleSection}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>示例（可选）</span>
                  <Button size="small" appearance="subtle" onClick={addExample}>
                    + 添加示例
                  </Button>
                </div>
                {formExamples.map((example, index) => (
                  <div key={index} className={classes.exampleItem}>
                    <div className={classes.exampleInput}>
                      <Input
                        size="small"
                        value={example.text}
                        onChange={(_, data) => updateExample(index, 'text', data.value)}
                        placeholder="问题文本示例"
                        style={{ marginBottom: '4px' }}
                      />
                      <Input
                        size="small"
                        value={example.explanation}
                        onChange={(_, data) => updateExample(index, 'explanation', data.value)}
                        placeholder="说明"
                      />
                    </div>
                    <Button
                      size="small"
                      appearance="subtle"
                      icon={<Delete16Regular />}
                      onClick={() => removeExample(index)}
                    />
                  </div>
                ))}
              </div>
            </DialogContent>
            <DialogActions>
              <Button
                appearance="primary"
                onClick={handleSave}
                disabled={saving}
                icon={saving ? <Spinner size="tiny" /> : undefined}
              >
                {editingRule ? '保存' : '创建'}
              </Button>
              <Button appearance="secondary" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={(_, data) => !data.open && setDeleteDialogOpen(false)}>
        <DialogSurface className={classes.dialogSurface}>
          <DialogBody>
            <DialogTitle>删除规则</DialogTitle>
            <DialogContent>
              <div style={{ 
                padding: '16px', 
                backgroundColor: tokens.colorPaletteRedBackground1, 
                borderRadius: '8px',
                marginBottom: '12px',
                border: `1px solid ${tokens.colorPaletteRedBorder1}`
              }}>
                <div style={{ fontSize: '13px', color: tokens.colorPaletteRedForeground1 }}>
                  确定要删除这条规则吗？此操作无法撤销。
                </div>
              </div>
            </DialogContent>
            <DialogActions>
              <Button appearance="secondary" onClick={() => setDeleteDialogOpen(false)}>
                取消
              </Button>
              <Button
                appearance="primary"
                style={{ backgroundColor: tokens.colorPaletteRedBackground3 }}
                onClick={handleConfirmDelete}
                disabled={deleting}
                icon={deleting ? <Spinner size="tiny" /> : <Delete16Regular />}
              >
                {deleting ? '删除中...' : '确认删除'}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </>
  )
}
