import { useState, useEffect } from 'react'
import { Cascader, Spin } from 'antd'
import type { CascaderProps } from 'antd'
import { getDocumentTypes } from '../services/api'
import type { DocumentTypeWithSubtypes } from '../types/rule'

interface CascaderOption {
    value: string
    label: string
    children?: CascaderOption[]
}

interface DocumentCategorySelectorProps {
    value?: string[]
    onChange?: (value: string[], typeId?: string, subtypeId?: string) => void
    placeholder?: string
    disabled?: boolean
}

/**
 * 文书分类级联选择器
 * 用于选择文书类型和子类型
 */
export function DocumentCategorySelector({
    value,
    onChange,
    placeholder = '请选择文书分类',
    disabled = false
}: DocumentCategorySelectorProps) {
    const [options, setOptions] = useState<CascaderOption[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        loadDocumentTypes()
    }, [])

    const loadDocumentTypes = async () => {
        setLoading(true)
        try {
            const types = await getDocumentTypes()
            const cascaderOptions = transformToOptions(types)
            setOptions(cascaderOptions)
        } catch (error) {
            console.error('Failed to load document types:', error)
        } finally {
            setLoading(false)
        }
    }

    const transformToOptions = (types: DocumentTypeWithSubtypes[]): CascaderOption[] => {
        return types.map(type => ({
            value: type.id,
            label: type.name,
            children: type.subtypes.map(subtype => ({
                value: subtype.id,
                label: subtype.name
            }))
        }))
    }

    const handleChange: CascaderProps<CascaderOption>['onChange'] = (selectedValue) => {
        const stringValue = selectedValue as string[]
        if (onChange) {
            const typeId = stringValue[0]
            const subtypeId = stringValue[1]
            onChange(stringValue, typeId, subtypeId)
        }
    }

    if (loading) {
        return <Spin size="small" />
    }

    return (
        <Cascader
            options={options}
            value={value}
            onChange={handleChange}
            placeholder={placeholder}
            disabled={disabled}
            style={{ width: '100%' }}
            expandTrigger="hover"
        />
    )
}

export default DocumentCategorySelector
