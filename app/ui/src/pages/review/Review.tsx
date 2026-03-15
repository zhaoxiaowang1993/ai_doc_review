import { CheckOutlined, DownOutlined, LeftOutlined, ReloadOutlined, RightOutlined, UpOutlined, ZoomInOutlined, ZoomOutOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Drawer, List, Modal, Select, Spin, Tag } from 'antd'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import './ReviewPage.css'
import { IssueDetailsPanel } from '../../components/IssueDetailsPanel'
import { IssueListItem } from '../../components/IssueListItem'
import { DocumentIRViewer } from '../../components/DocumentIRViewer'
import { addAnnotation, deleteAnnotation, initAnnotations } from '../../services/annotations'
import { streamApi, getDocument, getDocumentTypes, getReviewRulesState, downloadDocumentFile, getDocumentIssues, getReviewStatus, startReview } from '../../services/api'
import { APIEvent } from '../../types/api-events'
import { Issue, IssueStatus } from '../../types/issue'
import { issueRiskLevel, issueTypeLabel, normalizeIssueStatus } from '../../i18n/labels'
import type { ReviewRuleSnapshotItem } from '../../types/rule'
import { accentColors } from '../../theme'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

function Review() {
  const [searchParams] = useSearchParams()

  const [docId, setDocId] = useState<string>()
  const [docMimeType, setDocMimeType] = useState<string>()
  const [pdfData, setPdfData] = useState<{ data: Uint8Array }>()
  const [pdfLoadError, setPdfLoadError] = useState<string>()
  const [numPages, setNumPages] = useState<number>()
  const [pageNumber, setPageNumber] = useState(1)
  const [zoom, setZoom] = useState(1.0)
  const [pdfContainerWidth, setPdfContainerWidth] = useState(700)

  const [issues, setIssues] = useState<Issue[]>([])
  const [selectedIssueId, setSelectedIssueId] = useState<string>()
  const [selectedAnchorIndex, setSelectedAnchorIndex] = useState(0)

  const [checkInProgress, setCheckInProgress] = useState(false)
  const [checkComplete, setCheckComplete] = useState(false)
  const [checkError, setCheckError] = useState<string>()

  const [hideTypesFilter, setHideTypesFilter] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<string[]>(Object.values(IssueStatus))
  const [latestRuleIds, setLatestRuleIds] = useState<string[]>([])
  const [totalRulesCount, setTotalRulesCount] = useState(0)
  const [rulesDrawerOpen, setRulesDrawerOpen] = useState(false)
  const [reviewRules, setReviewRules] = useState<ReviewRuleSnapshotItem[]>([])
  const [reviewRulesLoading, setReviewRulesLoading] = useState(false)
  const [reviewRulesError, setReviewRulesError] = useState<string>()
  const [rulesChangedSinceReview, setRulesChangedSinceReview] = useState(false)

  // 文档分类信息
  const [documentCategoryLabel, setDocumentCategoryLabel] = useState<string>()

  const abortControllerRef = useRef<AbortController>()
  const expectedAbortRef = useRef<WeakSet<AbortController>>(new WeakSet())
  const latestRuleIdsRef = useRef<string[]>([])
  const pdfContainerRef = useRef<HTMLDivElement>(null)
  const selectedAnnotIdRef = useRef<string>()
  const isPdfDoc = (docMimeType ?? '').startsWith('application/pdf')

  // Keep ref in sync with state
  useEffect(() => {
    latestRuleIdsRef.current = latestRuleIds
  }, [latestRuleIds])

  const selectedIssue = useMemo(
    () => issues.find((i) => i.id === selectedIssueId),
    [issues, selectedIssueId],
  )

  const selectedAnchors = useMemo(() => {
    const anchors = (selectedIssue?.location as any)?.anchors
    return Array.isArray(anchors) ? anchors : []
  }, [selectedIssue])

  const canNavigateAnchors = selectedAnchors.length > 1

  const applyHighlight = useCallback((pageNum: number, bbox: number[]) => {
    try {
      if (selectedAnnotIdRef.current) {
        const pdfBytes = deleteAnnotation(selectedAnnotIdRef.current)
        selectedAnnotIdRef.current = undefined
        setPdfData({ data: pdfBytes })
      }
    } catch {
    }
    try {
      const [pdfBytes, annot] = addAnnotation(pageNum, bbox, { r: 255, g: 64, b: 64 })
      selectedAnnotIdRef.current = annot.id
      setPdfData({ data: pdfBytes })
    } catch {
    }
  }, [])

  const gotoAnchor = useCallback((index: number) => {
    if (!selectedIssue) return
    const anchors = Array.isArray((selectedIssue.location as any)?.anchors) ? (selectedIssue.location as any).anchors : []
    const target = anchors[index]
    if (!target?.page_num || !target?.bounding_box?.length) return
    setSelectedAnchorIndex(index)
    setPageNumber(target.page_num)
    applyHighlight(target.page_num, target.bounding_box)
  }, [applyHighlight, selectedIssue])

  const gotoPrevAnchor = useCallback(() => {
    if (!canNavigateAnchors) return
    const next = Math.max(0, selectedAnchorIndex - 1)
    gotoAnchor(next)
  }, [canNavigateAnchors, gotoAnchor, selectedAnchorIndex])

  const gotoNextAnchor = useCallback(() => {
    if (!canNavigateAnchors) return
    const next = Math.min(selectedAnchors.length - 1, selectedAnchorIndex + 1)
    gotoAnchor(next)
  }, [canNavigateAnchors, gotoAnchor, selectedAnchorIndex, selectedAnchors.length])

  const filteredIssues = useMemo(() => {
    return issues
      .filter(
        (issue) =>
          statusFilter.includes(
            normalizeIssueStatus(issue.status as unknown as string),
          ) && !hideTypesFilter.includes(issue.type),
      )
      .slice()
      .sort((a, b) => {
        const al = a.location as any
        const bl = b.location as any
        const at = al?.type
        const bt = bl?.type

        if (at === 'ir_anchor' && bt === 'ir_anchor') {
          const ai = Number(al?.para_index)
          const bi = Number(bl?.para_index)
          const aiOk = Number.isFinite(ai)
          const biOk = Number.isFinite(bi)
          if (aiOk && biOk && ai !== bi) return ai - bi
          if (aiOk && !biOk) return -1
          if (!aiOk && biOk) return 1
          const an = String(al?.node_id ?? '')
          const bn = String(bl?.node_id ?? '')
          if (an && bn && an !== bn) return an.localeCompare(bn)
          return 0
        }

        const ap = Number(al?.page_num ?? al?.para_index ?? 0)
        const bp = Number(bl?.page_num ?? bl?.para_index ?? 0)
        return ap - bp
      })
  }, [issues, statusFilter, hideTypesFilter])

  const types = useMemo(() => {
    const map = new Map<string, number>()
    for (const i of issues) map.set(i.type, (map.get(i.type) ?? 0) + 1)
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  }, [issues])

  const allIssueTypes = useMemo(() => types.map(([t]) => t), [types])
  const typeCountByType = useMemo(() => new Map(types), [types])

  const metrics = useMemo(() => {
    const normalized = issues.map((i) => normalizeIssueStatus(i.status as unknown as string))
    const total = issues.length
    const processed = normalized.filter((s) => s === IssueStatus.Accepted || s === IssueStatus.Dismissed).length
    const high = issues.filter((i) => issueRiskLevel(i.type) === '高').length
    const medium = issues.filter((i) => issueRiskLevel(i.type) === '中').length
    const low = issues.filter((i) => issueRiskLevel(i.type) === '低').length
    const highOpen = issues.filter((i) => issueRiskLevel(i.type) === '高' && normalizeIssueStatus(i.status as unknown as string) === IssueStatus.NotReviewed).length

    const conclusion =
      total === 0
        ? { label: '—', tone: 'informative' as const }
        : highOpen > 0
          ? { label: '需整改', tone: 'danger' as const }
          : processed === total
            ? { label: '可出具结论', tone: 'success' as const }
            : { label: '审阅中', tone: 'warning' as const }

    return { total, processed, high, medium, low, conclusion }
  }, [issues])

  const refreshRulesState = useCallback(async (showLoading = true) => {
    if (!docId) return
    if (showLoading) setReviewRulesLoading(true)
    setReviewRulesError(undefined)
    try {
      const state = await getReviewRulesState(docId)
      setReviewRules(state.snapshot_rules)
      setTotalRulesCount(state.snapshot_rules.length)
      setLatestRuleIds(state.latest_rule_ids)
      setRulesChangedSinceReview(state.rules_changed_since_review)
    } catch (e) {
      setReviewRulesError(e instanceof Error ? e.message : String(e))
    } finally {
      if (showLoading) setReviewRulesLoading(false)
    }
  }, [docId])

  const runCheck = useCallback((force = false, reset = true) => {
    if (!docId) return
    setCheckInProgress(true)
    setCheckError(undefined)
    setCheckComplete(false)
    if (reset) setIssues([])

    // Build query params - use ref to get current rule IDs without adding dependency
    const params = new URLSearchParams()
    if (force) params.set('force', 'true')
    const currentRuleIds = latestRuleIdsRef.current
    if (currentRuleIds.length > 0) {
      currentRuleIds.forEach(id => params.append('rule_ids', id))
    }
    const queryString = params.toString()
    const apiPath = `${docId}/issues${queryString ? `?${queryString}` : ''}`

    // 取消上一次可能的请求
    if (abortControllerRef.current) {
      expectedAbortRef.current.add(abortControllerRef.current)
      abortControllerRef.current.abort()
    }
    // 创建新的 controller
    const controller = new AbortController()
    abortControllerRef.current = controller

    streamApi(
      apiPath,
      (msg) => {
        switch (msg.event) {
          case APIEvent.Issues: {
            const newIssues = JSON.parse(msg.data) as Issue[]
            setIssues((prev) => {
              if (prev.length === 0) return newIssues
              const seen = new Set(prev.map((i) => i.id))
              const merged = prev.slice()
              for (const it of newIssues) {
                if (seen.has(it.id)) continue
                seen.add(it.id)
                merged.push(it)
              }
              return merged
            })
            let pdfBytesWithAnnotations: Uint8Array | undefined
            for (const i of newIssues) {
              const loc = i.location as any
              if (loc && loc.page_num && loc.bounding_box?.length) {
                try {
                  ;[pdfBytesWithAnnotations] = addAnnotation(loc.page_num, loc.bounding_box)
                } catch {
                  // ignore
                }
              }
            }
            if (pdfBytesWithAnnotations) setPdfData({ data: pdfBytesWithAnnotations })
            break
          }
          case APIEvent.Error: {
            throw new Error(msg.data)
          }
          case APIEvent.Complete: {
            // 完成时主动断开连接，但必须使用当前的 controller，避免误伤新请求
            expectedAbortRef.current.add(controller)
            controller.abort()
            setCheckComplete(true)
            setCheckInProgress(false)
            refreshRulesState(false)
            break
          }
          default:
            throw new Error(`未知事件：${msg.event}`)
        }
      },
      (err) => {
        if (err.name === 'AbortError' || err.message.includes('aborted')) {
          if (expectedAbortRef.current.has(controller)) return
          setCheckError('连接已中断，请重试。')
          setCheckInProgress(false)
          return
        }
        setCheckError(err.message)
        setCheckInProgress(false)
      },
      controller, // 传入当前的 controller
    )
  }, [docId, refreshRulesState])

  const handleReReview = useCallback(() => {
    if (!rulesChangedSinceReview) {
      runCheck(true)
      return
    }
    Modal.confirm({
      title: '确认重新审阅？',
      content: '此操作将清空历史问题列表，并按照最新适用规则审阅，是否继续？',
      okText: '继续',
      cancelText: '取消',
      onOk: () => runCheck(true),
    })
  }, [rulesChangedSinceReview, runCheck])

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages)
  }

  function handleSelectIssue(issue: Issue) {
    const isPdf = (docMimeType ?? '').startsWith('application/pdf')
    // 检查是否点击同一个 issue（取消选择）
    if (selectedIssueId === issue.id) {
      setSelectedIssueId(undefined)
      setSelectedAnchorIndex(0)
      if (!isPdf) return
      try {
        if (selectedAnnotIdRef.current) {
          const pdfBytes = deleteAnnotation(selectedAnnotIdRef.current)
          selectedAnnotIdRef.current = undefined
          setPdfData({ data: pdfBytes })
        }
      } catch {
      }
      return
    }

    // 清除旧的注释
    setSelectedAnchorIndex(0)
    if (!isPdf) {
      setSelectedIssueId(issue.id)
      return
    }
    try {
      if (selectedAnnotIdRef.current) {
        const pdfBytes = deleteAnnotation(selectedAnnotIdRef.current)
        selectedAnnotIdRef.current = undefined
        setPdfData({ data: pdfBytes })
      }
    } catch {
    }

    // 设置新选中的 issue
    setSelectedIssueId(issue.id)

    const anchors = Array.isArray((issue.location as any)?.anchors) ? (issue.location as any).anchors : []
    const target = anchors[0] ?? (issue.location as any)
    if (target?.page_num) setPageNumber(target.page_num)
    if (target?.bounding_box?.length) applyHighlight(target.page_num, target.bounding_box)
  }

  function handleUpdateIssue(updatedIssue: Issue) {
    setIssues((prev) => {
      const idx = prev.findIndex((i) => i.id === updatedIssue.id)
      if (idx === -1) return prev
      const next = prev.slice()
      next[idx] = updatedIssue
      return next
    })
  }

  useEffect(() => {
    const d = searchParams.get('doc_id')
    if (d) setDocId(d)
    else setPdfLoadError('URL 中未指定文档')
  }, [searchParams])

  // 加载文档元数据获取分类信息
  useEffect(() => {
    async function loadDocumentMetadata() {
      if (!docId) return
      try {
        const docMeta = await getDocument(docId)
        setDocMimeType(docMeta?.mime_type)
        if (docMeta?.subtype_id) {
          // 获取分类名称用于展示
          const types = await getDocumentTypes()
          for (const type of types) {
            const subtype = type.subtypes.find(s => s.id === docMeta.subtype_id)
            if (subtype) {
              setDocumentCategoryLabel(`${type.name} / ${subtype.name}`)
              break
            }
          }
        }
      } catch (e) {
        // 文档可能没有分类信息（旧文档），静默处理
        console.log('Document metadata not found:', e)
      }
    }
    loadDocumentMetadata()
  }, [docId])

  useEffect(() => {
    async function loadPdf(id: string) {
      setPdfLoadError(undefined)
      try {
        const pdfBlob = await downloadDocumentFile(id)
        const pdfByteArray = new Uint8Array(await pdfBlob.arrayBuffer())
        const pdfBytesWithAnnot = initAnnotations(pdfByteArray)
        setPdfData({ data: pdfBytesWithAnnot })
      } catch (e) {
        setPdfLoadError(`加载失败：${e instanceof Error ? e.message : String(e)}`)
      }
    }
    if (!docId) return
    if ((docMimeType ?? '').startsWith('application/pdf')) {
      loadPdf(docId)
      return
    }
    setPdfData(undefined)
    setPdfLoadError(undefined)
  }, [docId, docMimeType])

  useEffect(() => {
    refreshRulesState()
  }, [refreshRulesState])

  useEffect(() => {
    async function initReview() {
      if (!docId) return
      setCheckError(undefined)
      try {
        let status = await getReviewStatus(docId)
        if (status.status === 'not_started') {
          status = await startReview(docId)
        }

        const existing = await getDocumentIssues(docId)
        setIssues(existing)

        const inProgress = status.status === 'running' || status.status === 'cancel_requested'
        const isComplete = status.status === 'completed'
        const isFailed = status.status === 'failed' || status.status === 'cancelled'

        setCheckInProgress(inProgress)
        setCheckComplete(isComplete)
        if (isFailed && status.error_message) setCheckError(status.error_message)

        if (inProgress) {
          runCheck(false, false)
          return
        }
        if (!isComplete && existing.length === 0) {
          runCheck(false, true)
        }
      } catch (e) {
        setCheckError(e instanceof Error ? e.message : String(e))
        setCheckInProgress(false)
      }
    }
    initReview()
    return () => {
      if (abortControllerRef.current) {
        expectedAbortRef.current.add(abortControllerRef.current)
        abortControllerRef.current.abort()
      }
    }
  }, [docId, runCheck])

  // Update PDF container width on resize
  useEffect(() => {
    const updateWidth = () => {
      if (pdfContainerRef.current) {
        const containerWidth = pdfContainerRef.current.offsetWidth
        // Leave some padding (24px on each side)
        const availableWidth = containerWidth - 48
        setPdfContainerWidth(availableWidth)
      }
    }
    updateWidth()
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])

  const checkButtonIcon = checkComplete ? <CheckOutlined /> : <ReloadOutlined />
  const conclusionTagColor =
    metrics.conclusion.tone === 'success'
      ? 'success'
      : metrics.conclusion.tone === 'danger'
        ? 'error'
        : metrics.conclusion.tone === 'warning'
          ? 'warning'
          : 'processing'

  return (
    <div className="review-layout">
      {/* LEFT */}
      <div className="review-panel review-left">
        <div className="review-left-header">
          <div className="review-count-row">
            <div className="review-top-tags">
              {documentCategoryLabel && <Tag color="blue">{documentCategoryLabel}</Tag>}
            </div>
            <Tag color="processing">{filteredIssues.length}/{issues.length} 条</Tag>
          </div>
          <div className="review-filter-row">
            <Button size="small" type={statusFilter.length === Object.values(IssueStatus).length ? 'primary' : 'default'} onClick={() => setStatusFilter(Object.values(IssueStatus))}>
              全部
            </Button>
            <Button size="small" type={statusFilter.length === 1 && statusFilter.includes(IssueStatus.NotReviewed) ? 'primary' : 'default'} onClick={() => setStatusFilter([IssueStatus.NotReviewed])}>
              待处理
            </Button>
            <Button size="small" type={statusFilter.length === 1 && statusFilter.includes(IssueStatus.Accepted) ? 'primary' : 'default'} onClick={() => setStatusFilter([IssueStatus.Accepted])}>
              已采纳
            </Button>
            <Button size="small" type={statusFilter.length === 1 && statusFilter.includes(IssueStatus.Dismissed) ? 'primary' : 'default'} onClick={() => setStatusFilter([IssueStatus.Dismissed])}>
              已忽略
            </Button>
          </div>
          {allIssueTypes.length > 0 && (
            <Select
              className="review-type-filter"
              allowClear
              placeholder="全部分类"
              value={
                hideTypesFilter.length === 0
                  ? undefined
                  : allIssueTypes.find((t) => !hideTypesFilter.includes(t))
              }
              options={allIssueTypes.map((t) => ({
                value: t,
                label: `${issueTypeLabel(t)} (${typeCountByType.get(t) ?? 0})`,
              }))}
              onChange={(value) => {
                const selected = value as string | undefined
                if (!selected) {
                  setHideTypesFilter([])
                  return
                }
                setHideTypesFilter(allIssueTypes.filter((t) => t !== selected))
              }}
            />
          )}
        </div>
        <div className="review-left-list">
          {checkError && (
            <Alert type="error" showIcon message="审核失败" description={checkError} />
          )}
          {filteredIssues.map((issue) => (
            <IssueListItem key={issue.id} issue={issue} selected={selectedIssueId === issue.id} onSelect={handleSelectIssue} />
          ))}
          {checkInProgress && (
            <div className="review-analyze-status">
              <Spin size="small" /> 分析中…
            </div>
          )}
          {!checkInProgress && filteredIssues.length === 0 && (
            <div className="review-empty">暂无问题</div>
          )}
        </div>
      </div>

      {/* CENTER */}
      <div className="review-panel review-center">
        <div className="review-toolbar">
          {isPdfDoc ? (
            <>
              <div className="review-toolbar-section">
                <Button size="small" icon={<UpOutlined />} onClick={() => setPageNumber((p) => Math.max(1, p - 1))} disabled={pageNumber === 1} />
                <Button size="small" icon={<DownOutlined />} onClick={() => setPageNumber((p) => Math.min(numPages ?? p + 1, p + 1))} disabled={!!numPages && pageNumber === numPages} />
                <span className="review-page-info">{pageNumber}/{numPages ?? '-'}</span>
                {canNavigateAnchors && (
                  <>
                    <Button size="small" icon={<LeftOutlined />} onClick={gotoPrevAnchor} disabled={selectedAnchorIndex <= 0} />
                    <span className="review-page-info">命中 {selectedAnchorIndex + 1}/{selectedAnchors.length}</span>
                    <Button size="small" icon={<RightOutlined />} onClick={gotoNextAnchor} disabled={selectedAnchorIndex >= selectedAnchors.length - 1} />
                  </>
                )}
              </div>
              <div className="review-toolbar-section">
                <Button size="small" icon={<ZoomOutOutlined />} onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} />
                <span className="review-zoom-info">{Math.round(zoom * 100)}%</span>
                <Button size="small" icon={<ZoomInOutlined />} onClick={() => setZoom((z) => Math.min(2, +(z + 0.1).toFixed(2)))} />
                <Button size="small" type="primary" icon={checkButtonIcon} loading={checkInProgress} onClick={handleReReview}>
                  重新审阅
                </Button>
              </div>
            </>
          ) : (
            <div className="review-toolbar-section">
              <Button size="small" type="primary" icon={checkButtonIcon} loading={checkInProgress} onClick={handleReReview}>
                重新审阅
              </Button>
            </div>
          )}
        </div>
        <div ref={pdfContainerRef} className="review-pdf-compare-container review-pdf-compare-single">
          <div className="review-pdf-pane">
            <div className="review-pdf-wrap">
              <div className="review-pdf-card">
                {isPdfDoc ? (
                  <>
                    {pdfLoadError && (
                      <Alert type="error" showIcon message={pdfLoadError} />
                    )}
                    <Document file={pdfData} onLoadSuccess={onDocumentLoadSuccess} loading={<Spin />} noData={<Spin />}>
                      <Page pageNumber={pageNumber} width={Math.floor(pdfContainerWidth * zoom)} loading={<Spin />} />
                    </Document>
                  </>
                ) : (
                  <>
                    {docId ? <DocumentIRViewer docId={docId} selectedIssue={selectedIssue} /> : null}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT */}
      <div className="review-right">
        <Card
          size="small"
          className="review-overview-card"
          title="审阅概览"
          extra={
            <Button type="link" size="small" onClick={() => setRulesDrawerOpen(true)}>
              查看审阅规则
            </Button>
          }
          bodyStyle={{ padding: 0 }}
          headStyle={{ padding: '10px 14px' }}
        >
          <div className="review-overview-grid">
            <div className="review-metric-item">
              <span className="review-metric-label">进度</span>
              <span className="review-metric-value">{metrics.processed}/{metrics.total}</span>
            </div>
            <div className="review-metric-item">
              <span className="review-metric-label">高/中/低</span>
              <span className="review-metric-value" style={{ display: 'flex', gap: '4px' }}>
                <span style={{ color: accentColors.danger }}>{metrics.high}</span>
                <span style={{ color: 'rgba(0, 0, 0, 0.45)' }}>/</span>
                <span style={{ color: accentColors.warning }}>{metrics.medium}</span>
                <span style={{ color: 'rgba(0, 0, 0, 0.45)' }}>/</span>
                <span style={{ color: accentColors.success }}>{metrics.low}</span>
              </span>
            </div>
            <div className="review-metric-item">
              <span className="review-metric-label">结论</span>
              <Tag color={conclusionTagColor}>{metrics.conclusion.label}</Tag>
            </div>
          </div>
        </Card>

        <div className="review-right-body">
          <IssueDetailsPanel docId={docId ?? ''} issue={selectedIssue} onUpdate={handleUpdateIssue} />
        </div>

        <Drawer
          title="审阅规则"
          placement="right"
          width={380}
          open={rulesDrawerOpen}
          onClose={() => setRulesDrawerOpen(false)}
          destroyOnClose
        >
          {reviewRulesLoading ? (
            <div className="review-analyze-status">
              <Spin size="small" /> 加载中…
            </div>
          ) : reviewRulesError ? (
            <Alert type="error" showIcon message="加载规则失败" description={reviewRulesError} />
          ) : (
            <>
              {rulesChangedSinceReview && (
                <Alert
                  banner
                  type="warning"
                  showIcon
                  message="此文档审阅后，有适用规则发生了变更。如需按照新规则类型审阅，请重新审阅"
                  style={{ marginBottom: 12 }}
                />
              )}
              <div style={{ marginBottom: 12 }}>
                <Tag>{reviewRules.length}/{totalRulesCount}</Tag>
              </div>
              <List
                dataSource={reviewRules}
                renderItem={(rule) => {
                  const riskColor = rule.risk_level === '高' ? 'error' : rule.risk_level === '中' ? 'warning' : 'success'
                  return (
                    <List.Item style={{ paddingLeft: 0, paddingRight: 0 }}>
                      <List.Item.Meta
                        title={
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontWeight: 600 }}>{rule.name}</span>
                            <Tag color={riskColor}>{rule.risk_level}</Tag>
                          </div>
                        }
                        description={rule.description}
                      />
                    </List.Item>
                  )
                }}
              />
            </>
          )}
        </Drawer>
      </div>
    </div>
  )
}

export default Review
