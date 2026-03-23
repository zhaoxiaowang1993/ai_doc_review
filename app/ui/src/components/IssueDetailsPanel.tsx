import { CheckOutlined, CloseOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Empty, Modal, Space, Switch, Tag, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { callApi } from '../services/api'
import { Issue, IssueStatus } from '../types/issue'
import { normalizeIssueStatus } from '../i18n/labels'

export function IssueDetailsPanel({
  docId,
  issue,
  onUpdate,
  onIrMaybeUpdated,
}: {
  docId: string
  issue?: Issue
  onUpdate: (updatedIssue: Issue) => void
  onIrMaybeUpdated?: () => void
}) {
  const [error, setError] = useState<string>()

  const [decisionOpen, setDecisionOpen] = useState(false)
  const [decisionAction, setDecisionAction] = useState<'accept' | 'dismiss'>('accept')
  const [submittingDecision, setSubmittingDecision] = useState(false)
  const [noIssue, setNoIssue] = useState(false)
  const [userSuggestion, setUserSuggestion] = useState('')

  const current = issue

  const defaults = useMemo(() => {
    if (!current) return { explanation: '', suggestedFix: '' }
    return {
      explanation: current.modified_fields?.explanation ?? current.explanation,
      suggestedFix: current.modified_fields?.suggested_fix ?? current.suggested_fix,
    }
  }, [current])

  useEffect(() => {
    setError(undefined)
    setDecisionOpen(false)
    setNoIssue(false)
    setUserSuggestion('')
  }, [issue?.id])

  function openDecision(action: 'accept' | 'dismiss') {
    if (!current) return
    setDecisionAction(action)
    setNoIssue(false)
    setUserSuggestion('')
    setDecisionOpen(true)
  }

  async function submitDecision() {
    if (!current) return
    if (decisionAction === 'dismiss' && !noIssue && userSuggestion.trim().length < 5) {
      message.warning('你认为该段有问题时，请填写至少 5 个字的修改建议')
      return
    }
    setError(undefined)
    try {
      setSubmittingDecision(true)
      const loc = (current.location as any) ?? {}
      const isIr = loc?.type === 'ir_anchor' || !!loc?.node_id
      const response = await callApi(`${docId}/issues/${current.id}/decision`, 'POST', {
        action: decisionAction,
        no_issue: decisionAction === 'dismiss' ? noIssue : false,
        user_suggestion: decisionAction === 'dismiss' ? userSuggestion : '',
      })
      const payload = await response.json() as { issue: Issue, task?: { id: string } }
      onUpdate(payload.issue)
      setDecisionOpen(false)
      if (isIr && payload.task?.id) {
        void pollTaskAndRefreshIr(payload.task.id)
      }
      if (payload.task?.id) {
        message.success(`操作成功，已创建任务 ${payload.task.id}`)
      } else {
        message.success('操作成功')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSubmittingDecision(false)
    }
  }

  async function pollTaskAndRefreshIr(taskId: string) {
    for (let i = 0; i < 20; i++) {
      try {
        const response = await callApi(`tasks/${taskId}`)
        const task = await response.json() as { status?: string, error_message?: string }
        const status = task.status ?? ''
        if (status === 'completed') {
          onIrMaybeUpdated?.()
          message.success('文档原文已完成自动修订')
          return
        }
        if (status === 'failed' || status === 'skipped') {
          message.warning(task.error_message || '自动修订未完成，请检查任务状态')
          return
        }
      } catch {
        message.warning('自动修订状态查询失败，请稍后刷新查看')
        return
      }
      await new Promise((resolve) => setTimeout(resolve, 500))
    }
    message.warning('自动修订仍在处理中，请稍后刷新查看结果')
  }

  // Empty state
  if (!current) {
    return (
      <Card size="small" title="审阅处理">
        <Empty description="选择左侧问题列表中的问题以进行处理" />
      </Card>
    )
  }

  const normalizedStatus = normalizeIssueStatus(current.status as unknown as string)
  const editable = normalizedStatus === IssueStatus.NotReviewed

  return (
    <>
      {error && <Alert type="error" showIcon message="操作失败" description={error} />}

      <Card size="small" title="审阅处理">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'rgba(0, 0, 0, 0.65)' }}>问题说明</div>
            <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 10, background: '#fafafa', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
              {defaults.explanation || '暂无'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'rgba(0, 0, 0, 0.65)' }}>修改建议</div>
            <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 10, background: '#fafafa', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
              {defaults.suggestedFix || '暂无'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'rgba(0, 0, 0, 0.65)' }}>触发规则快照</div>
            <Space size={[6, 6]} wrap>
              {(current.triggered_rules_snapshot ?? []).map((rule, idx) => (
                <Tag key={`${rule.rule_id ?? rule.rule_name}-${idx}`} color="blue">
                  {rule.rule_name}
                </Tag>
              ))}
              {(current.triggered_rules_snapshot ?? []).length === 0 && <Tag>暂无</Tag>}
            </Space>
            {(current.triggered_rules_snapshot ?? []).map((rule, idx) => (
              <div key={`content-${rule.rule_id ?? rule.rule_name}-${idx}`} style={{ marginTop: 6, fontSize: 12, color: 'rgba(0,0,0,0.72)' }}>
                {rule.rule_name}：{rule.rule_content}
              </div>
            ))}
          </div>

          {editable && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Space size={8} wrap>
                <Button size="small" danger icon={<CloseOutlined />} onClick={() => openDecision('dismiss')}>
                  不采纳
                </Button>
                <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => openDecision('accept')}>
                  采纳
                </Button>
              </Space>
            </div>
          )}
        </Space>
      </Card>

      <Modal
        title={decisionAction === 'accept' ? '采纳确认' : '不采纳确认'}
        open={decisionOpen}
        onCancel={() => setDecisionOpen(false)}
        okText="确认"
        cancelText="取消"
        okButtonProps={{ loading: submittingDecision }}
        onOk={submitDecision}
        destroyOnClose
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <Tag color="geekblue">AI 问题说明</Tag>
            <div style={{ marginTop: 8, border: '1px solid #d9d9d9', borderRadius: 8, padding: 10, background: '#fafafa', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
              {defaults.explanation || '暂无'}
            </div>
          </div>
          <div>
            <Tag color="purple">AI 修改建议</Tag>
            <div style={{ marginTop: 8, border: '1px solid #d9d9d9', borderRadius: 8, padding: 10, background: '#fafafa', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
              {defaults.suggestedFix || '暂无'}
            </div>
          </div>
          {decisionAction === 'dismiss' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Switch checked={noIssue} onChange={setNoIssue} />
                <span style={{ fontSize: 12 }}>是否认为此段无问题</span>
              </div>
              {!noIssue && (
                <div>
                  <Tag color="orange">你的修改建议（必填）</Tag>
                  <textarea
                    value={userSuggestion}
                    onChange={(e) => setUserSuggestion(e.target.value)}
                    rows={4}
                    style={{ width: '100%', marginTop: 8, border: '1px solid #d9d9d9', borderRadius: 8, padding: 10, resize: 'vertical' }}
                    placeholder="请输入至少 5 个字的修改建议"
                  />
                </div>
              )}
            </>
          )}
          {decisionAction === 'accept' && (
            <Alert type="info" showIcon message="你正在采纳 AI 修改建议，确认后将按该建议创建后续任务。" />
          )}
          {decisionAction === 'dismiss' && noIssue && (
            <Alert type="warning" showIcon message="你选择了“此段无问题”，确认后将只驳回 AI，不修改原文。" />
          )}
        </Space>
      </Modal>
    </>
  )
}
