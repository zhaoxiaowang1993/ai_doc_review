import { useState, useCallback } from 'react'
import { Modal, Upload, Button, message, Space } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import type { UploadFile, RcFile } from 'antd/es/upload/interface'
import { DocumentCategorySelector } from './DocumentCategorySelector'
import { uploadDocument, getDocumentIRStatus } from '../services/api'

const { Dragger } = Upload

interface UploadModalProps {
    open: boolean
    onClose: () => void
    onSuccess?: (docId: string) => void
}

/**
 * 文件上传模态框
 * 包含文件选择和文书分类选择功能
 */
export function UploadModal({ open, onClose, onSuccess }: UploadModalProps) {
    const [fileList, setFileList] = useState<UploadFile[]>([])
    const [categoryValue, setCategoryValue] = useState<string[]>([])
    const [subtypeId, setSubtypeId] = useState<string | undefined>()
    const [uploading, setUploading] = useState(false)
    const [fileTypeError, setFileTypeError] = useState<string>()

    const handleCategoryChange = useCallback((value: string[], _typeId?: string, selectedSubtypeId?: string) => {
        setCategoryValue(value)
        setSubtypeId(selectedSubtypeId)
    }, [])

    const handleBeforeUpload = useCallback((file: RcFile) => {
        const name = (file.name ?? '').toLowerCase()
        const ok = name.endsWith('.pdf') || name.endsWith('.docx') || name.endsWith('.txt')
        if (!ok) {
            setFileList([])
            setFileTypeError('不支持此格式的文件，请上传 pdf/docx/txt 格式的文件')
            return false
        }
        setFileTypeError(undefined)
        setFileList([file as unknown as UploadFile])
        return false // 阻止自动上传
    }, [])

    const handleRemove = useCallback(() => {
        setFileList([])
        setFileTypeError(undefined)
    }, [])

    const handleUpload = async () => {
        if (fileList.length === 0) {
            message.error('请选择要上传的文件')
            return
        }
        if (!subtypeId) {
            message.error('请选择文书分类')
            return
        }

        setUploading(true)
        try {
            const file = fileList[0] as unknown as File
            const result = await uploadDocument(file, subtypeId)
            const filename = (file.name ?? '').toLowerCase()
            const isPdf = filename.endsWith('.pdf')
            if (!isPdf) {
                message.loading({ content: '文档解析在后台进行，可离开页面；解析完成后可进入审阅。', duration: 0, key: 'ir' })
                const deadline = Date.now() + 120_000
                while (Date.now() < deadline) {
                    const st = await getDocumentIRStatus(result.doc_id)
                    if (st.status === 'ready') break
                    if (st.status === 'failed') throw new Error(st.error_message ?? 'IR 生成失败')
                    await new Promise((r) => setTimeout(r, 1000))
                }
                const st = await getDocumentIRStatus(result.doc_id)
                if (st.status !== 'ready') throw new Error('IR 生成超时，请稍后在文档列表中重试进入审阅')
                message.success({ content: '文件上传成功', key: 'ir' })
            } else {
                message.success('文件上传成功')
            }
            onSuccess?.(result.doc_id)
            handleClose()
        } catch (error) {
            console.error('Upload failed:', error)
            const msg = error instanceof Error ? error.message : '上传失败'
            message.error({ content: msg, key: 'ir', duration: 3 })
        } finally {
            setUploading(false)
        }
    }

    const handleClose = () => {
        setFileList([])
        setCategoryValue([])
        setSubtypeId(undefined)
        onClose()
    }

    const canUpload = fileList.length > 0 && subtypeId

    return (
        <Modal
            title="上传文书"
            open={open}
            onCancel={handleClose}
            footer={[
                <Button key="cancel" onClick={handleClose}>
                    取消
                </Button>,
                <Button
                    key="upload"
                    type="primary"
                    onClick={handleUpload}
                    loading={uploading}
                    disabled={!canUpload}
                >
                    开始上传
                </Button>
            ]}
            width={520}
        >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div>
                    <div style={{ marginBottom: 8, fontWeight: 500 }}>选择文件</div>
                    <Dragger
                        fileList={fileList}
                        beforeUpload={handleBeforeUpload}
                        onRemove={handleRemove}
                        accept=".pdf,.docx,.txt"
                        maxCount={1}
                    >
                        <p className="ant-upload-drag-icon">
                            <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">点击或拖拽文件到此区域</p>
                        <p className="ant-upload-hint">支持 PDF / DOCX / TXT</p>
                    </Dragger>
                    {fileTypeError && (
                        <div style={{ marginTop: 6, fontSize: 12, color: '#ff4d4f' }}>
                            {fileTypeError}
                        </div>
                    )}
                </div>

                <div>
                    <div style={{ marginBottom: 8, fontWeight: 500 }}>
                        文书分类 <span style={{ color: '#ff4d4f' }}>*</span>
                    </div>
                    <DocumentCategorySelector
                        value={categoryValue}
                        onChange={handleCategoryChange}
                        placeholder="请选择文书类型和子类"
                    />
                    <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        选择分类后，系统将自动加载对应的审核规则
                    </div>
                </div>
            </Space>
        </Modal>
    )
}

export default UploadModal
