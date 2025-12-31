import {
  Badge,
  Button,
  Card,
  CardHeader,
  Divider,
  Input,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  Spinner,
  Toolbar,
  ToolbarButton,
  makeStyles,
  tokens,
} from '@fluentui/react-components'
import {
  CheckmarkFilled,
  ChevronDown16Regular,
  ChevronUp16Regular,
  PanelLeftContractRegular,
  PanelLeftExpandRegular,
  SearchRegular,
  ZoomInRegular,
  ZoomOutRegular,
} from '@fluentui/react-icons'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { IssueDetailsPanel } from '../../components/IssueDetailsPanel'
import { IssueListItem } from '../../components/IssueListItem'
import { RulesPanel } from '../../components/RulesPanel'
import { addAnnotation, deleteAnnotation, initAnnotations } from '../../services/annotations'
import { streamApi } from '../../services/api'
import { getBlob } from '../../services/storage'
import { APIEvent } from '../../types/api-events'
import { Issue, IssueStatus } from '../../types/issue'
import { issueRiskLevel, issueRiskTone, issueStatusLabel, issueTypeDescription, issueTypeLabel, normalizeIssueStatus } from '../../i18n/labels'
import { accentColors } from '../../theme'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

const useStyles = makeStyles({
  layout: {
    display: 'grid',
    gridTemplateColumns: '280px minmax(0, 1fr) 340px',
    gap: '16px',
    height: 'calc(100vh - 120px)',
    overflow: 'hidden',
  },
  // ========== PANEL ==========
  panel: {
    borderRadius: '12px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    height: '100%',
    overflow: 'hidden',
  },
  // ========== LEFT ==========
  left: {
    display: 'flex',
    flexDirection: 'column',
  },
  leftHeader: {
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    flexShrink: 0,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  countRow: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  docName: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '150px',
  },
  searchInput: {
    width: '100%',
  },
  filterRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  filterBtn: {
    minWidth: 'auto',
    fontSize: '12px',
  },
  filterBtnActive: {
    backgroundColor: tokens.colorBrandBackground2,
  },
  leftList: {
    padding: '8px 12px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    flexGrow: 1,
    minHeight: 0,
  },
  // ========== CENTER ==========
  center: {
    display: 'flex',
    flexDirection: 'column',
  },
  toolbar: {
    padding: '8px 12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  toolbarSection: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  pageInfo: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    minWidth: '60px',
    textAlign: 'center',
  },
  zoomInfo: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    minWidth: '48px',
    textAlign: 'center',
  },
  // ========== PDF COMPARISON ==========
  pdfCompareContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '2px',
    flexGrow: 1,
    overflow: 'hidden',
    backgroundColor: tokens.colorNeutralStroke2,
  },
  pdfCompareSingle: {
    gridTemplateColumns: '1fr',
  },
  pdfPane: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    backgroundColor: tokens.colorNeutralBackground3,
  },
  pdfPaneHeader: {
    padding: '6px 12px',
    fontSize: '11px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground3,
    backgroundColor: tokens.colorNeutralBackground2,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  pdfWrap: {
    padding: '12px',
    overflow: 'auto',
    display: 'flex',
    justifyContent: 'center',
    flexGrow: 1,
    backgroundColor: tokens.colorNeutralBackground3,
  },
  pdfCard: {
    padding: 0,
    backgroundColor: '#fff',
    borderRadius: '4px',
    boxShadow: tokens.shadow16,
  },
  // ========== RIGHT ==========
  right: {
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    padding: '12px',
    height: '100%',
    minHeight: 0,
  },
  // ========== OVERVIEW ==========
  accordion: {
    borderRadius: '10px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    overflow: 'hidden',
  },
  accordionItem: {
    '&:not(:last-child)': {
      borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    },
  },
  accordionHeader: {
    padding: '12px 14px',
    fontSize: '12px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer',
    backgroundColor: 'transparent',
    transitionProperty: 'background-color',
    transitionDuration: '150ms',
    '&:hover': {
      backgroundColor: tokens.colorNeutralBackground2,
    },
  },
  accordionIcon: {
    fontSize: '14px',
    color: tokens.colorNeutralForeground3,
    transitionProperty: 'transform',
    transitionDuration: '200ms',
  },
  accordionIconOpen: {
    transform: 'rotate(180deg)',
  },
  accordionContent: {
    backgroundColor: tokens.colorNeutralBackground2,
  },
  // ========== OVERVIEW ==========
  overviewCard: {
    borderRadius: '10px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    overflow: 'hidden',
  },
  overviewHeader: {
    padding: '10px 14px',
    fontSize: '12px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  overviewGrid: {
    display: 'flex',
    gap: '10px',
    padding: '12px 14px',
    alignItems: 'stretch',
  },
  metricItem: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 12px',
    borderRadius: '8px',
    backgroundColor: tokens.colorNeutralBackground2,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  metricLabel: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
  },
  metricValue: {
    fontSize: '14px',
    fontWeight: 700,
    color: tokens.colorNeutralForeground1,
  },
  // ========== TYPE CARDS ==========
  typeCards: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0',
    maxHeight: '240px',
    overflowY: 'auto',
  },
  typeCard: {
    padding: '10px 14px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    transitionProperty: 'background-color',
    transitionDuration: '150ms',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    '&:last-child': {
      borderBottom: 'none',
    },
    '&:hover': {
      backgroundColor: tokens.colorNeutralBackground3,
    },
  },
  typeInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    flexGrow: 1,
    minWidth: 0,
  },
  typeName: {
    fontSize: '13px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
  },
  typeDesc: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
    lineHeight: '1.4',
  },
  typeCount: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
  },
  analyzeStatus: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    padding: '10px 12px',
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
  },
  noIssues: {
    color: tokens.colorNeutralForeground3,
    padding: '16px 12px',
    textAlign: 'center',
    fontSize: '12px',
    lineHeight: '1.6',
  },
})

function Review() {
  const classes = useStyles()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [docId, setDocId] = useState<string>()
  const [originalPdfData, setOriginalPdfData] = useState<{ data: Uint8Array }>()
  const [pdfData, setPdfData] = useState<{ data: Uint8Array }>()
  const [pdfLoadError, setPdfLoadError] = useState<string>()
  const [pdfLoaded, setPdfLoaded] = useState(false)
  const [numPages, setNumPages] = useState<number>()
  const [pageNumber, setPageNumber] = useState(1)
  const [zoom, setZoom] = useState(1.0)
  const [compareMode, setCompareMode] = useState(true)
  const [pdfContainerWidth, setPdfContainerWidth] = useState(700)

  const [issues, setIssues] = useState<Issue[]>([])
  const [selectedIssueId, setSelectedIssueId] = useState<string>()
  const [selectedAnnotId, setSelectedAnnotId] = useState<string>()

  const [checkInProgress, setCheckInProgress] = useState(false)
  const [checkComplete, setCheckComplete] = useState(false)
  const [checkError, setCheckError] = useState<string>()

  const [hideTypesFilter, setHideTypesFilter] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<string[]>(Object.values(IssueStatus))
  const [query, setQuery] = useState('')
  const [enabledRuleIds, setEnabledRuleIds] = useState<string[]>([])
  const [totalRulesCount, setTotalRulesCount] = useState(0)
  const [rulesExpanded, setRulesExpanded] = useState(false)
  const [typesExpanded, setTypesExpanded] = useState(false)

  const abortControllerRef = useRef<AbortController>()
  const enabledRuleIdsRef = useRef<string[]>([])
  const pdfContainerRef = useRef<HTMLDivElement>(null)

  // Keep ref in sync with state
  useEffect(() => {
    enabledRuleIdsRef.current = enabledRuleIds
  }, [enabledRuleIds])

  const selectedIssue = useMemo(
    () => issues.find((i) => i.id === selectedIssueId),
    [issues, selectedIssueId],
  )

  const filteredIssues = useMemo(() => {
    const q = query.trim()
    return issues
      .filter((issue) => statusFilter.includes(normalizeIssueStatus(issue.status as unknown as string)) && !hideTypesFilter.includes(issue.type))
      .filter((issue) => (q ? `${issue.text} ${issue.explanation} ${issue.suggested_fix}`.includes(q) : true))
      .slice()
      .sort((a, b) => (a.location?.page_num ?? 0) - (b.location?.page_num ?? 0))
  }, [issues, statusFilter, hideTypesFilter, query])

  const types = useMemo(() => {
    const map = new Map<string, number>()
    for (const i of issues) map.set(i.type, (map.get(i.type) ?? 0) + 1)
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  }, [issues])

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

  const runCheck = useCallback((force = false) => {
    if (!docId) return
    setCheckInProgress(true)
    setCheckError(undefined)
    setCheckComplete(false)
    setIssues([])

    // Build query params - use ref to get current rule IDs without adding dependency
    const params = new URLSearchParams()
    if (force) params.set('force', 'true')
    const currentRuleIds = enabledRuleIdsRef.current
    if (currentRuleIds.length > 0) {
      currentRuleIds.forEach(id => params.append('rule_ids', id))
    }
    const queryString = params.toString()
    const apiPath = `${docId}/issues${queryString ? `?${queryString}` : ''}`

    abortControllerRef.current = new AbortController()
    streamApi(
      apiPath,
      (msg) => {
        switch (msg.event) {
          case APIEvent.Issues: {
            const newIssues = JSON.parse(msg.data) as Issue[]
            setIssues((prev) => [...prev, ...newIssues])
            let pdfBytesWithAnnotations: Uint8Array | undefined
            for (const i of newIssues) {
              if (i.location && i.location.page_num && i.location.bounding_box?.length) {
                try {
                  ;[pdfBytesWithAnnotations] = addAnnotation(i.location.page_num, i.location.bounding_box)
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
            abortControllerRef.current?.abort()
            setCheckComplete(true)
            setCheckInProgress(false)
            break
          }
          default:
            throw new Error(`未知事件：${msg.event}`)
        }
      },
      (err) => {
        setCheckError(err.message)
        setCheckInProgress(false)
      },
      abortControllerRef.current,
    )
  }, [docId])

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages)
    setPdfLoaded(true)
  }

  function handleSelectIssue(issue: Issue) {
    // 检查是否点击同一个 issue（取消选择）
    if (selectedIssueId === issue.id) {
      setSelectedIssueId(undefined)
      setSelectedAnnotId((annotId) => {
        if (annotId) {
          const pdfBytes = deleteAnnotation(annotId)
          setPdfData({ data: pdfBytes })
        }
        return undefined
      })
      return
    }

    // 清除旧的注释
    setSelectedAnnotId((annotId) => {
      if (annotId) {
        const pdfBytes = deleteAnnotation(annotId)
        setPdfData({ data: pdfBytes })
      }
      return undefined
    })

    // 设置新选中的 issue
    setSelectedIssueId(issue.id)

    // 跳转到对应页面
    if (issue.location?.page_num) {
      setPageNumber(issue.location.page_num)
    }

    // 添加新的注释高亮
    if (issue.location?.bounding_box?.length) {
      try {
        const [pdfBytes, annot] = addAnnotation(
          issue.location.page_num,
          issue.location.bounding_box,
          { r: 255, g: 64, b: 64 }
        )
        setSelectedAnnotId(annot.id)
        setPdfData({ data: pdfBytes })
      } catch {
        // ignore
      }
    }
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

  function toggleTypeVisibility(type: string) {
    setHideTypesFilter((types) => (types.includes(type) ? types.filter((t) => t !== type) : [...types, type]))
  }

  useEffect(() => {
    const d = searchParams.get('document')
    if (d) setDocId(d)
    else setPdfLoadError('URL 中未指定文档')
  }, [searchParams])

  useEffect(() => {
    async function loadPdf(id: string) {
      setPdfLoadError(undefined)
      setPdfLoaded(false)
      try {
        const pdfBlob = await getBlob(id)
        const pdfByteArray = new Uint8Array(await pdfBlob.arrayBuffer())
        // Store original PDF for comparison
        setOriginalPdfData({ data: pdfByteArray.slice() })
        const pdfBytesWithAnnot = initAnnotations(pdfByteArray)
        setPdfData({ data: pdfBytesWithAnnot })
      } catch (e) {
        setPdfLoadError(`加载失败：${e instanceof Error ? e.message : String(e)}`)
      }
    }
    if (docId) loadPdf(docId)
  }, [docId])

  useEffect(() => {
    runCheck()
    return () => abortControllerRef.current?.abort()
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
  }, [compareMode])

  const checkButtonIcon = checkInProgress ? <Spinner size="tiny" /> : checkComplete ? <CheckmarkFilled /> : undefined

  return (
    <div className={classes.layout}>
      {/* LEFT */}
      <Card className={`${classes.panel} ${classes.left}`}>
        <div className={classes.leftHeader}>
          <div className={classes.countRow}>
            <Badge appearance="tint" color="informative" shape="rounded">
              {filteredIssues.length}/{issues.length} 条
            </Badge>
            <span className={classes.docName} title={docId ?? ''}>{docId ?? ''}</span>
          </div>
          <Input
            size="small"
            className={classes.searchInput}
            contentBefore={<SearchRegular />}
            placeholder="搜索问题…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className={classes.filterRow}>
            <Button
              size="small"
              appearance={statusFilter.length === Object.values(IssueStatus).length ? 'primary' : 'secondary'}
              className={classes.filterBtn}
              onClick={() => setStatusFilter(Object.values(IssueStatus))}
            >
              全部
            </Button>
            <Button
              size="small"
              appearance={statusFilter.length === 1 && statusFilter.includes(IssueStatus.NotReviewed) ? 'primary' : 'secondary'}
              className={classes.filterBtn}
              onClick={() => setStatusFilter([IssueStatus.NotReviewed])}
            >
              待处理
            </Button>
            <Button
              size="small"
              appearance={statusFilter.length === 1 && statusFilter.includes(IssueStatus.Accepted) ? 'primary' : 'secondary'}
              className={classes.filterBtn}
              onClick={() => setStatusFilter([IssueStatus.Accepted])}
            >
              已采纳
            </Button>
            <Button
              size="small"
              appearance={statusFilter.length === 1 && statusFilter.includes(IssueStatus.Dismissed) ? 'primary' : 'secondary'}
              className={classes.filterBtn}
              onClick={() => setStatusFilter([IssueStatus.Dismissed])}
            >
              已忽略
            </Button>
          </div>
        </div>
        <div className={classes.leftList}>
          {checkError && (
            <MessageBar intent="error">
              <MessageBarBody>
                <MessageBarTitle>审核失败</MessageBarTitle>
                {checkError}
              </MessageBarBody>
            </MessageBar>
          )}
          {filteredIssues.map((issue) => (
            <IssueListItem key={issue.id} issue={issue} selected={selectedIssueId === issue.id} onSelect={handleSelectIssue} />
          ))}
          {checkInProgress && (
            <div className={classes.analyzeStatus}>
              <Spinner size="tiny" /> 分析中…
            </div>
          )}
          {!checkInProgress && filteredIssues.length === 0 && (
            <div className={classes.noIssues}>暂无问题</div>
          )}
        </div>
      </Card>

      {/* CENTER */}
      <Card className={`${classes.panel} ${classes.center}`}>
        <div className={classes.toolbar}>
          <div className={classes.toolbarSection}>
            <Toolbar size="small">
              <ToolbarButton icon={<ChevronUp16Regular />} onClick={() => setPageNumber((p) => Math.max(1, p - 1))} disabled={pageNumber === 1} />
              <ToolbarButton icon={<ChevronDown16Regular />} onClick={() => setPageNumber((p) => Math.min(numPages ?? p + 1, p + 1))} disabled={!!numPages && pageNumber === numPages} />
            </Toolbar>
            <span className={classes.pageInfo}>{pageNumber}/{numPages ?? '-'}</span>
          </div>
          <div className={classes.toolbarSection}>
            <Button
              size="small"
              appearance={compareMode ? 'primary' : 'secondary'}
              icon={compareMode ? <PanelLeftContractRegular /> : <PanelLeftExpandRegular />}
              onClick={() => setCompareMode((m) => !m)}
            >
              {compareMode ? '单视图' : '对比'}
            </Button>
            <Button size="small" appearance="subtle" icon={<ZoomOutRegular />} onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} />
            <span className={classes.zoomInfo}>{Math.round(zoom * 100)}%</span>
            <Button size="small" appearance="subtle" icon={<ZoomInRegular />} onClick={() => setZoom((z) => Math.min(2, +(z + 0.1).toFixed(2)))} />
            <Button size="small" appearance="primary" icon={checkButtonIcon} disabledFocusable={checkInProgress} onClick={() => runCheck(true)}>
              重新审阅
            </Button>
            <Button size="small" appearance="secondary" onClick={() => navigate('/')}>
              返回
            </Button>
          </div>
        </div>
        <div ref={pdfContainerRef} className={`${classes.pdfCompareContainer} ${!compareMode ? classes.pdfCompareSingle : ''}`}>
          {/* Original PDF */}
          {compareMode && (
            <div className={classes.pdfPane}>
              <div className={classes.pdfPaneHeader}>原始文档</div>
              <div className={classes.pdfWrap}>
                <Card className={classes.pdfCard}>
                  {pdfLoadError && (
                    <MessageBar intent="error">
                      <MessageBarBody>{pdfLoadError}</MessageBarBody>
                    </MessageBar>
                  )}
                  <Document file={originalPdfData} loading={<Spinner />} noData={<Spinner />}>
                    <Page pageNumber={pageNumber} width={Math.floor((compareMode ? pdfContainerWidth / 2 : pdfContainerWidth) * zoom)} loading={<Spinner />} />
                  </Document>
                </Card>
              </div>
            </div>
          )}
          {/* Annotated PDF */}
          <div className={classes.pdfPane}>
            {compareMode && <div className={classes.pdfPaneHeader}>标注文档</div>}
            <div className={classes.pdfWrap}>
              <Card className={classes.pdfCard}>
                {pdfLoadError && !compareMode && (
                  <MessageBar intent="error">
                    <MessageBarBody>{pdfLoadError}</MessageBarBody>
                  </MessageBar>
                )}
                <Document file={pdfData} onLoadSuccess={onDocumentLoadSuccess} loading={<Spinner />} noData={<Spinner />}>
                  <Page pageNumber={pageNumber} width={Math.floor((compareMode ? pdfContainerWidth / 2 : pdfContainerWidth) * zoom)} loading={<Spinner />} />
                </Document>
              </Card>
            </div>
          </div>
        </div>
      </Card>

      {/* RIGHT */}
      <div className={classes.right}>
        <div className={classes.overviewCard}>
          <div className={classes.overviewHeader}>审阅概览</div>
          <div className={classes.overviewGrid}>
            <div className={classes.metricItem}>
              <span className={classes.metricLabel}>进度</span>
              <span className={classes.metricValue}>{metrics.processed}/{metrics.total}</span>
            </div>
            <div className={classes.metricItem}>
              <span className={classes.metricLabel}>高/中/低</span>
              <span className={classes.metricValue} style={{ display: 'flex', gap: '4px' }}>
                <span style={{ color: accentColors.danger }}>{metrics.high}</span>
                <span style={{ color: tokens.colorNeutralForeground3 }}>/</span>
                <span style={{ color: accentColors.warning }}>{metrics.medium}</span>
                <span style={{ color: tokens.colorNeutralForeground3 }}>/</span>
                <span style={{ color: accentColors.success }}>{metrics.low}</span>
              </span>
            </div>
            <div className={classes.metricItem}>
              <span className={classes.metricLabel}>结论</span>
              <Badge appearance="filled" shape="rounded" color={metrics.conclusion.tone} style={{ fontSize: '11px' }}>
                {metrics.conclusion.label}
              </Badge>
            </div>
          </div>
        </div>

        <IssueDetailsPanel docId={docId ?? ''} issue={selectedIssue} onUpdate={handleUpdateIssue} />

        <div className={classes.accordion}>
          {docId && (
            <div className={classes.accordionItem}>
              <div className={classes.accordionHeader} onClick={() => setRulesExpanded(!rulesExpanded)}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  审核规则
                  <Badge appearance="outline" size="small" color="informative">{enabledRuleIds.length}/{totalRulesCount}</Badge>
                </span>
                <ChevronDown16Regular className={`${classes.accordionIcon} ${rulesExpanded ? classes.accordionIconOpen : ''}`} />
              </div>
              {rulesExpanded && (
                <div className={classes.accordionContent}>
                  <RulesPanel
                    docId={docId}
                    enabledRuleIds={enabledRuleIds}
                    onEnabledRulesChange={setEnabledRuleIds}
                    onRulesCountChange={setTotalRulesCount}
                    hideHeader={true}
                  />
                </div>
              )}
            </div>
          )}

          <div className={classes.accordionItem}>
            <div className={classes.accordionHeader} onClick={() => setTypesExpanded(!typesExpanded)}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                问题分类
                {types.length > 0 && <Badge appearance="outline" size="small" color="informative">{types.length}</Badge>}
              </span>
              <ChevronDown16Regular className={`${classes.accordionIcon} ${typesExpanded ? classes.accordionIconOpen : ''}`} />
            </div>
            {typesExpanded && (
              <div className={classes.accordionContent}>
                <div className={classes.typeCards}>
                  {types.length === 0 && <div className={classes.noIssues}>暂无</div>}
                  {types.map(([type, count]) => (
                    <div key={type} className={classes.typeCard}>
                      <div className={classes.typeInfo}>
                        <div className={classes.typeName}>{issueTypeLabel(type)}</div>
                        <div className={classes.typeDesc}>{issueTypeDescription(type) ?? ''}</div>
                      </div>
                      <div className={classes.typeCount}>
                        <Badge appearance="tint" shape="rounded" color={issueRiskTone(type)}>{count}</Badge>
                        <Button appearance="subtle" size="small" onClick={() => toggleTypeVisibility(type)}>
                          {hideTypesFilter.includes(type) ? '显示' : '隐藏'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Review
