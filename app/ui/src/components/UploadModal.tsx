import { useState, useCallback } from 'react'
import { Modal, Upload, Button, message, Space } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import type { UploadFile, RcFile } from 'antd/es/upload/interface'
import { DocumentCategorySelector } from './DocumentCategorySelector'
import { uploadFile } from '../services/api'

const { Dragger } = Upload

interface UploadModalProps {
    open: boolean
    onClose: () => void
    onSuccess?: (filename: string, docId: string | null) => void
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

    const handleCategoryChange = useCallback((value: string[], _typeId?: string, selectedSubtypeId?: string) => {
        setCategoryValue(value)
        setSubtypeId(selectedSubtypeId)
    }, [])

    const handleBeforeUpload = useCallback((file: RcFile) => {
        // 只允许 PDF 文件
        const isPDF = file.type === 'application/pdf'
        if (!isPDF) {
            message.error('只支持上传 PDF 文件')
            return false
        }
        setFileList([file as unknown as UploadFile])
        return false // 阻止自动上传
    }, [])

    const handleRemove = useCallback(() => {
        setFileList([])
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
            const result = await uploadFile(file, subtypeId)
            message.success('文件上传成功')
            onSuccess?.(result.filename, result.doc_id)
            handleClose()
        } catch (error) {
            console.error('Upload failed:', error)
            message.error(error instanceof Error ? error.message : '上传失败')
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
                        accept=".pdf"
                        maxCount={1}
                    >
                        <p className="ant-upload-drag-icon">
                            <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">点击或拖拽 PDF 文件到此区域</p>
                        <p className="ant-upload-hint">仅支持 PDF 格式文件</p>
                    </Dragger>
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
