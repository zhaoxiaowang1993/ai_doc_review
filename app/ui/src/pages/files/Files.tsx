import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DialogTrigger,
  Divider,
  makeStyles,
  mergeClasses,
  MessageBar,
  MessageBarBody,
  MessageBarTitle,
  ProgressBar,
  SkeletonItem,
  Text,
  tokens,
} from '@fluentui/react-components'
import {
  ArrowUploadRegular,
  CloudArrowUpRegular,
  DeleteRegular,
  DocumentPdfRegular,
  FolderOpenRegular,
} from '@fluentui/react-icons'
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import pdfIcon from '../../assets/pdf.svg'
import { deleteBlob, listBlobs, uploadBlob, type LocalFileItem } from '../../services/storage'

const useStyles = makeStyles({
  page: { maxWidth: '1200px', margin: '0 auto' },
  // ========== HEADER ==========
  header: {
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: '16px',
    marginBottom: '16px',
  },
  titleWrap: { display: 'flex', flexDirection: 'column', gap: '4px' },
  title: {
    fontSize: '24px',
    fontWeight: 700,
    color: tokens.colorNeutralForeground1,
  },
  subtitle: {
    color: tokens.colorNeutralForeground3,
    fontSize: '13px',
  },
  headerActions: {
    display: 'flex',
    gap: '8px',
  },
  // ========== GRID ==========
  grid: {
    display: 'grid',
    gridTemplateColumns: '340px 1fr',
    gap: '16px',
    marginTop: '16px',
  },
  // ========== PANEL ==========
  panel: {
    borderRadius: '12px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  // ========== UPLOAD ==========
  uploadCard: {
    minHeight: '280px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '20px',
    cursor: 'pointer',
    border: `2px dashed ${tokens.colorNeutralStroke2}`,
    borderRadius: '10px',
    margin: '12px',
    backgroundColor: tokens.colorNeutralBackground2,
    transitionProperty: 'all',
    transitionDuration: '200ms',
    '&:hover': {
      borderTopColor: tokens.colorBrandStroke1,
      borderRightColor: tokens.colorBrandStroke1,
      borderBottomColor: tokens.colorBrandStroke1,
      borderLeftColor: tokens.colorBrandStroke1,
      backgroundColor: tokens.colorNeutralBackground3,
    },
  },
  uploadCardActive: {
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
    backgroundColor: tokens.colorBrandBackground2,
  },
  uploadIconWrap: {
    width: '64px',
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '16px',
    backgroundColor: tokens.colorBrandBackground2,
    marginBottom: '12px',
  },
  uploadIcon: {
    fontSize: '28px',
    color: tokens.colorBrandForeground1,
  },
  uploadTitle: {
    fontSize: '15px',
    fontWeight: 600,
    marginBottom: '6px',
    color: tokens.colorNeutralForeground1,
  },
  uploadHint: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
    marginBottom: '12px',
  },
  statsRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    justifyContent: 'center',
  },
  // ========== LIST ==========
  listHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
  },
  listTitle: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  listGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
    gap: '20px',
    padding: '20px 24px',
  },
  // ========== DOC CARD ==========
  docCard: {
    borderRadius: '10px',
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    cursor: 'pointer',
    transitionProperty: 'all',
    transitionDuration: '150ms',
    overflow: 'hidden',
    '&:hover': {
      borderTopColor: tokens.colorNeutralStroke1,
      borderRightColor: tokens.colorNeutralStroke1,
      borderBottomColor: tokens.colorNeutralStroke1,
      borderLeftColor: tokens.colorNeutralStroke1,
      transform: 'translateY(-2px)',
      boxShadow: tokens.shadow8,
    },
  },
  docPreview: {
    backgroundColor: tokens.colorNeutralBackground3,
    padding: '24px 12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  docIcon: {
    width: '48px',
    height: '48px',
  },
  docInfo: {
    padding: '14px 12px',
  },
  docName: {
    fontSize: '12px',
    fontWeight: 600,
    wordBreak: 'break-word',
    marginBottom: '2px',
    lineHeight: '1.3',
    color: tokens.colorNeutralForeground1,
  },
  docMeta: {
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
  },
  docActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    padding: '0 8px 8px',
  },
  deleteBtn: {
    minWidth: 'auto',
  },
  empty: {
    padding: '32px 16px',
    textAlign: 'center',
    color: tokens.colorNeutralForeground3,
  },
})

function Files() {
  const classes = useStyles()
  const navigate = useNavigate()

  const [fileList, setFileList] = useState<LocalFileItem[] | undefined>()
  const [error, setError] = useState<string | undefined>()
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | undefined>()
  const [deleting, setDeleting] = useState(false)

  const fileInput = useRef<HTMLInputElement | null>(null)

  const openDocument = useCallback(
    (filename: string) => navigate({ pathname: '/review', search: `?document=${filename}` }),
    [navigate],
  )

  const totalCount = fileList?.length ?? 0
  const recentDocs = useMemo(() => (fileList ?? []), [fileList])

  useEffect(() => {
    async function loadFileList() {
      try {
        const files = await listBlobs()
        setFileList(files)
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      }
    }
    loadFileList()
  }, [])

  const triggerPick = () => fileInput.current?.click()

  async function uploadFile(file: File) {
    setError(undefined)
    setUploading(true)
    try {
      await uploadBlob(file)
      const files = await listBlobs()
      setFileList(files)
      openDocument(file.name)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleUploadFile = async (event: FormEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0]
    if (!file) return
    await uploadFile(file)
  }

  const refreshList = async () => {
    try {
      const files = await listBlobs()
      setFileList(files)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setError(undefined)
    setDeleting(true)
    try {
      await deleteBlob(deleteTarget)
      const files = await listBlobs()
      setFileList(files)
      setDeleteTarget(undefined)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className={classes.page}>
      <div className={classes.header}>
        <div className={classes.titleWrap}>
          <div className={classes.title}>文档库</div>
          <div className={classes.subtitle}>统一管理审阅任务、问题识别与整改记录</div>
        </div>
        <div className={classes.headerActions}>
          <Button appearance="secondary" icon={<FolderOpenRegular />} onClick={refreshList}>
            刷新
          </Button>
          <Button appearance="primary" icon={<ArrowUploadRegular />} onClick={triggerPick}>
            上传文档
          </Button>
        </div>
      </div>

      {error && (
        <MessageBar intent="error" style={{ marginBottom: 12 }}>
          <MessageBarBody>
            <MessageBarTitle>请求失败</MessageBarTitle>
            {error}
          </MessageBarBody>
        </MessageBar>
      )}

      <Divider />

      <div className={classes.grid}>
        <Card
          className={classes.panel}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={async (e) => {
            e.preventDefault()
            setDragOver(false)
            const file = e.dataTransfer.files?.[0]
            if (file) await uploadFile(file)
          }}
        >
          <div
            className={mergeClasses(classes.uploadCard, dragOver && classes.uploadCardActive)}
            onClick={triggerPick}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className={classes.uploadIconWrap}>
                <CloudArrowUpRegular className={classes.uploadIcon} />
              </div>
              <div className={classes.uploadTitle}>拖拽文件到此处上传</div>
              <div className={classes.uploadHint}>支持 PDF 格式 · 点击选择文件</div>
              <div className={classes.statsRow}>
                <Badge appearance="tint" color="informative" shape="rounded">
                  <DocumentPdfRegular style={{ marginRight: 4 }} />
                  已入库 {totalCount} 份
                </Badge>
              </div>
            </div>
          </div>
          <input
            type="file"
            onChange={handleUploadFile}
            ref={fileInput}
            style={{ display: 'none' }}
            accept="application/pdf"
          />
        </Card>

        <Card className={classes.panel}>
          <div className={classes.listHeader}>
            <div className={classes.listTitle}>
              <Text weight="semibold">全部文档</Text>
              <Text size={200} style={{ color: tokens.colorNeutralForeground3 }}>
                点击进入审核工作台
              </Text>
            </div>
            <Badge appearance="filled" color="informative" shape="rounded">
              {totalCount}
            </Badge>
          </div>
          <Divider />
          <div className={classes.listGrid}>
            {!fileList &&
              Array.from({ length: 6 }, (_, i) => (
                <SkeletonItem key={i} style={{ height: 120, borderRadius: 10 }} />
              ))}
            {fileList && fileList.length === 0 && (
              <div className={classes.empty}>暂无文档，请上传 PDF 开始审核</div>
            )}
            {recentDocs.map((file) => (
              <div key={file.name} className={classes.docCard}>
                <div className={classes.docPreview} onClick={() => openDocument(file.name)}>
                  <img className={classes.docIcon} src={pdfIcon} alt="PDF" />
                </div>
                <div className={classes.docInfo} onClick={() => openDocument(file.name)}>
                  <div className={classes.docName}>{file.name}</div>
                  <div className={classes.docMeta}>
                    {file.lastModified ? file.lastModified.toLocaleDateString() : '已上传'}
                  </div>
                </div>
                <div className={classes.docActions}>
                  <Button
                    appearance="subtle"
                    size="small"
                    icon={<DeleteRegular />}
                    className={classes.deleteBtn}
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(file.name)
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Dialog open={uploading}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>正在上传…</DialogTitle>
            <DialogContent>
              <ProgressBar />
              <div style={{ marginTop: 10, color: tokens.colorNeutralForeground3, fontSize: 12 }}>
                上传完成后将自动进入审核页面
              </div>
            </DialogContent>
          </DialogBody>
        </DialogSurface>
      </Dialog>

      <Dialog open={!!deleteTarget} onOpenChange={(_, data) => !data.open && setDeleteTarget(undefined)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>确认删除</DialogTitle>
            <DialogContent>
              <div style={{ color: tokens.colorNeutralForeground2, fontSize: 14 }}>
                确定要删除文档 <strong>{deleteTarget}</strong> 吗？此操作不可撤销。
              </div>
            </DialogContent>
            <DialogActions>
              <Button appearance="secondary" onClick={() => setDeleteTarget(undefined)}>
                取消
              </Button>
              <Button appearance="primary" onClick={handleDelete} disabled={deleting}>
                {deleting ? '删除中…' : '确认删除'}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  )
}

export default Files
