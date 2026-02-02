import { CheckOutlined, CloseOutlined, EditOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Empty, Input, Modal, Space, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { callApi } from '../services/api'
import { DismissalFeedback, Issue, IssueStatus, ModifiedFields } from '../types/issue'
import { normalizeIssueStatus } from '../i18n/labels'

function buildModifiedFields(modifiedExplanation?: string, modifiedSuggestedFix?: string): ModifiedFields | undefined {
  const modifiedFields: ModifiedFields = {}
  if (modifiedExplanation) modifiedFields.explanation = modifiedExplanation
  if (modifiedSuggestedFix) modifiedFields.suggested_fix = modifiedSuggestedFix
  return Object.keys(modifiedFields).length ? modifiedFields : undefined
}

export function IssueDetailsPanel({
  docId,
  issue,
  onUpdate,
}: {
  docId: string
  issue?: Issue
  onUpdate: (updatedIssue: Issue) => void
}) {
  const [error, setError] = useState<string>()

  const [accepting, setAccepting] = useState(false)
  const [dismissing, setDismissing] = useState(false)

  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedback, setFeedback] = useState<DismissalFeedback>()
  const [submittingFeedback, setSubmittingFeedback] = useState(false)

  const [hitlOpen, setHitlOpen] = useState(false)
  const [hitlSubmitting, setHitlSubmitting] = useState(false)
  const [hitlError, setHitlError] = useState<string>()
  const [hitlSuggestedFix, setHitlSuggestedFix] = useState<string>('')

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
    setFeedback(undefined)
    setFeedbackOpen(false)
    setHitlOpen(false)
    setHitlError(undefined)
    setHitlSuggestedFix('')
  }, [issue?.id])

  async function handleAccept() {
    if (!current) return
    setError(undefined)
    try {
      setAccepting(true)
      const response = await callApi(
        `${docId}/issues/${current.id}/accept`,
        'PATCH',
      )
      const updatedIssue = (await response.json()) as Issue
      onUpdate(updatedIssue)
      message.success('操作成功')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAccepting(false)
    }
  }

  async function handleDismiss() {
    if (!current) return
    setError(undefined)
    try {
      setDismissing(true)
      const response = await callApi(`${docId}/issues/${current.id}/dismiss`, 'PATCH')
      const updatedIssue = (await response.json()) as Issue
      onUpdate(updatedIssue)
      message.success('操作成功')
      setFeedbackOpen(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDismissing(false)
    }
  }

  async function handleSubmitFeedback() {
    if (!current) return
    setError(undefined)
    try {
      setSubmittingFeedback(true)
      await callApi(`${docId}/issues/${current.id}/feedback`, 'PATCH', feedback)
      setFeedbackOpen(false)
      message.success('操作成功')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSubmittingFeedback(false)
    }
  }

  function openHitlEditDialog() {
    if (!current) return
    setHitlError(undefined)
    setHitlSuggestedFix(defaults.suggestedFix)
    setHitlOpen(true)
  }

  async function runHitlDecision() {
    if (!current) return
    setHitlSubmitting(true)
    setHitlError(undefined)
    try {
      const response = await callApi(
        `${docId}/issues/${current.id}/accept`,
        'PATCH',
        buildModifiedFields(undefined, hitlSuggestedFix),
      )
      const updatedIssue = (await response.json()) as Issue
      onUpdate(updatedIssue)
      setHitlOpen(false)
      message.success('操作成功')
    } catch (e) {
      setHitlError(e instanceof Error ? e.message : String(e))
    } finally {
      setHitlSubmitting(false)
    }
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
            <Input.TextArea
              value={defaults.explanation}
              readOnly={true}
              autoSize={{ minRows: 4, maxRows: 10 }}
            />
          </div>

          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'rgba(0, 0, 0, 0.65)' }}>修改建议</div>
            <Input.TextArea
              value={defaults.suggestedFix}
              readOnly={true}
              autoSize={{ minRows: 4, maxRows: 10 }}
            />
          </div>

          {editable && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Space size={8} wrap>
                <Button size="small" icon={<EditOutlined />} onClick={openHitlEditDialog}>
                  人工复核
                </Button>
                <Button size="small" danger icon={<CloseOutlined />} loading={dismissing} onClick={handleDismiss}>
                  不采纳
                </Button>
                <Button size="small" type="primary" icon={<CheckOutlined />} loading={accepting} onClick={handleAccept}>
                  采纳
                </Button>
              </Space>
            </div>
          )}
        </Space>
      </Card>

      <Modal
        title="不采纳原因（可选）"
        open={feedbackOpen}
        onCancel={() => setFeedbackOpen(false)}
        okText="提交"
        cancelText="关闭"
        okButtonProps={{ loading: submittingFeedback }}
        onOk={handleSubmitFeedback}
        destroyOnClose
      >
        <div style={{ fontSize: 12, color: 'rgba(0, 0, 0, 0.65)', marginBottom: 8 }}>用于改进审阅与规则策略</div>
        <Input.TextArea
          value={feedback?.reason}
          placeholder="说明为何不采纳该建议，以及更合适的判断方式（可选）…"
          onChange={(e) => setFeedback({ ...feedback, reason: e.target.value })}
          autoSize={{ minRows: 5, maxRows: 10 }}
        />
      </Modal>

      <Modal
        title="人工复核"
        open={hitlOpen}
        onCancel={() => setHitlOpen(false)}
        okText="确认执行"
        cancelText="取消"
        okButtonProps={{ loading: hitlSubmitting }}
        onOk={runHitlDecision}
        destroyOnClose
      >
        {hitlError && <Alert type="error" showIcon message="错误" description={hitlError} style={{ marginBottom: 12 }} />}
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'rgba(0, 0, 0, 0.65)' }}>修改建议（可编辑）</div>
            <Input.TextArea
              value={hitlSuggestedFix}
              onChange={(e) => setHitlSuggestedFix(e.target.value)}
              autoSize={{ minRows: 5, maxRows: 12 }}
            />
          </div>
        </Space>
      </Modal>
    </>
  )
}
