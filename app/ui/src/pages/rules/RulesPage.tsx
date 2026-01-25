import { useState, useEffect, useMemo } from 'react'
import {
    Button,
    Input,
    Select,
    Table,
    Tooltip,
    Modal,
    Form,
    Switch,
    Tabs,
    Space,
    Cascader,
    Spin,
    message,
    Popconfirm,
} from 'antd'
import {
    PlusOutlined,
    DeleteOutlined,
    EditOutlined,
    SearchOutlined,
    ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type {
    ReviewRule, CreateRuleRequest, UpdateRuleRequest,
    DocumentTypeWithSubtypes
} from '../../types/rule'
import { RiskLevel, RuleStatus, RuleType, RuleSource } from '../../types/rule'
import { getRules, createRule, updateRule, deleteRule, getDocumentTypes } from '../../services/api'
import './RulesPage.css'

const { TabPane } = Tabs
const { Option } = Select
const { TextArea } = Input

// 风险等级颜色配置
const RISK_COLORS: Record<RiskLevel, string> = {
    [RiskLevel.High]: '#cf1322',
    [RiskLevel.Medium]: '#d48806',
    [RiskLevel.Low]: '#389e0d',
}

function RulesPage() {
    const [rules, setRules] = useState<ReviewRule[]>([])
    const [documentTypes, setDocumentTypes] = useState<DocumentTypeWithSubtypes[]>([])
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<string>(RuleType.Applicable)

    // Filters
    const [searchQuery, setSearchQuery] = useState('')
    const [statusFilter, setStatusFilter] = useState<string>('all')
    const [riskFilter, setRiskFilter] = useState<string>('all')
    const [docTypeFilter, setDocTypeFilter] = useState<string[]>([])  // 改为数组支持多选

    // Dialog state
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [editingRule, setEditingRule] = useState<ReviewRule | null>(null)
    const [form] = Form.useForm()
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        loadData()
    }, [])

    async function loadData() {
        setLoading(true)
        try {
            const [rulesData, typesData] = await Promise.all([
                getRules(),
                getDocumentTypes()
            ])
            setRules(rulesData)
            setDocumentTypes(typesData)
        } catch (error) {
            console.error('Failed to load data:', error)
            message.error('加载数据失败')
        } finally {
            setLoading(false)
        }
    }

    // Build cascader options for document types
    const cascaderOptions = useMemo(() => {
        const options = [
            {
                value: 'universal',
                label: '通用（适用于所有文书）',
            }
        ]

        documentTypes.forEach(type => {
            if (type.subtypes && type.subtypes.length > 0) {
                options.push({
                    value: type.id,
                    label: type.name,
                    children: type.subtypes.map(subtype => ({
                        value: subtype.id,
                        label: subtype.name,
                    })),
                } as any)
            }
        })

        return options
    }, [documentTypes])

    // 筛选选项 - 支持文书类型和子类
    const docTypeFilterOptions = useMemo(() => {
        const options: { value: string; label: string; isType?: boolean }[] = [
            { value: 'universal', label: '通用' },
        ]
        documentTypes.forEach(type => {
            // 添加文书类型
            options.push({ value: type.id, label: type.name, isType: true })
            // 添加子类
            type.subtypes?.forEach(subtype => {
                options.push({ value: subtype.id, label: `  └ ${subtype.name}` })
            })
        })
        return options
    }, [documentTypes])

    // 获取某个文书类型下的所有子类 ID
    function getSubtypeIdsForType(typeId: string): string[] {
        const type = documentTypes.find(t => t.id === typeId)
        return type?.subtypes?.map(s => s.id) || []
    }

    // Filter and sort rules
    const filteredRules = useMemo(() => {
        let result = rules.filter(rule => {
            // Filter by tab (rule type)
            if (rule.rule_type !== activeTab) return false
            // Filter by source (only show custom rules)
            if (rule.source !== RuleSource.Custom) return false
            // Filter by search query
            if (searchQuery) {
                const query = searchQuery.toLowerCase()
                if (!rule.name.toLowerCase().includes(query) &&
                    !rule.description.toLowerCase().includes(query)) {
                    return false
                }
            }
            // Filter by status
            if (statusFilter !== 'all' && rule.status !== statusFilter) return false
            // Filter by risk level
            if (riskFilter !== 'all' && rule.risk_level !== riskFilter) return false
            // Filter by document type/subtype (二级筛选)
            if (docTypeFilter.length > 0) {
                const matchesAll = docTypeFilter.every(filterId => {
                    if (filterId === 'universal') {
                        return rule.is_universal
                    }
                    // 检查是否是文书类型 ID
                    const isTypeId = documentTypes.some(t => t.id === filterId)
                    if (isTypeId) {
                        if (rule.type_ids.includes(filterId)) return true
                        const subtypeIds = getSubtypeIdsForType(filterId)
                        return subtypeIds.some(sid => rule.subtype_ids.includes(sid))
                    }
                    // 否则是子类 ID，直接匹配
                    return rule.subtype_ids.includes(filterId)
                })
                // 不再自动包含“通用”规则，仅当筛选条件包含 universal 时才保留
                if (!matchesAll) {
                    return false
                }
            }
            return true
        })

        // Sort by created_at descending
        result.sort((a, b) => {
            const dateA = new Date(a.created_at).getTime()
            const dateB = new Date(b.created_at).getTime()
            return dateB - dateA
        })

        return result
    }, [rules, activeTab, searchQuery, statusFilter, riskFilter, docTypeFilter, documentTypes])

    function getScopeName(scopeId: string): string {
        for (const type of documentTypes) {
            if (type.id === scopeId) return type.name
        }
        for (const type of documentTypes) {
            for (const subtype of type.subtypes) {
                if (subtype.id === scopeId) return subtype.name
            }
        }
        return scopeId
    }

    function openCreateModal() {
        setEditingRule(null)
        form.resetFields()
        form.setFieldsValue({
            risk_level: RiskLevel.Low,  // 默认低风险
            rule_type: activeTab,
            subtype_ids: [],
        })
        setIsModalOpen(true)
    }

    function openEditModal(rule: ReviewRule) {
        setEditingRule(rule)
        const subtypeValues: string[][] = []
        if (rule.is_universal) {
            subtypeValues.push(['universal'])
        } else {
            rule.type_ids?.forEach(typeId => {
                subtypeValues.push([typeId])
            })
            rule.subtype_ids?.forEach(subtypeId => {
                for (const type of documentTypes) {
                    for (const subtype of type.subtypes) {
                        if (subtype.id === subtypeId) {
                            subtypeValues.push([type.id, subtypeId])
                            return
                        }
                    }
                }
                subtypeValues.push([subtypeId])
            })
        }

        form.setFieldsValue({
            name: rule.name,
            description: rule.description,
            risk_level: rule.risk_level,
            subtype_ids: subtypeValues,
        })
        setIsModalOpen(true)
    }

    function handleCascaderChange(value: string[][]) {
        const hasUniversal = (value || []).some(path => path[path.length - 1] === 'universal')
        if (!hasUniversal) return
        if (value.length === 1 && value[0][0] === 'universal') return
        form.setFieldsValue({ subtype_ids: [['universal']] })
    }

    async function handleSubmit() {
        try {
            const values = await form.validateFields()
            setSubmitting(true)

            const selectedPaths: string[][] = values.subtype_ids || []
            const selectedLastValues = selectedPaths.map(path => path[path.length - 1])
            const isUniversal = selectedLastValues.includes('universal')

            const typeIds: string[] = []
            const subtypeIds: string[] = []
            if (!isUniversal) {
                selectedPaths.forEach(path => {
                    if (path.length === 1) {
                        typeIds.push(path[0])
                    } else if (path.length >= 2) {
                        subtypeIds.push(path[path.length - 1])
                    }
                })
            }
            const dedupTypeIds = Array.from(new Set(typeIds))
            const dedupSubtypeIds = Array.from(new Set(subtypeIds))

            if (editingRule) {
                const updateData: UpdateRuleRequest = {
                    name: values.name,
                    description: values.description,
                    risk_level: values.risk_level,
                    is_universal: isUniversal,
                    type_ids: dedupTypeIds,
                    subtype_ids: dedupSubtypeIds,
                }
                await updateRule(editingRule.id, updateData)
                message.success('规则更新成功')
            } else {
                const createData: CreateRuleRequest = {
                    name: values.name,
                    description: values.description,
                    risk_level: values.risk_level,
                    rule_type: activeTab as RuleType,
                    source: RuleSource.Custom,
                    is_universal: isUniversal,
                    type_ids: dedupTypeIds,
                    subtype_ids: dedupSubtypeIds,
                }
                await createRule(createData)
                message.success('规则创建成功')
            }
            setIsModalOpen(false)
            loadData()
        } catch (error) {
            console.error('Failed to save rule:', error)
            message.error('保存失败')
        } finally {
            setSubmitting(false)
        }
    }

    async function handleDelete(ruleId: string) {
        try {
            await deleteRule(ruleId)
            message.success('规则已删除')
            loadData()
        } catch (error) {
            console.error('Failed to delete rule:', error)
            message.error('删除失败')
        }
    }

    async function handleToggleStatus(rule: ReviewRule) {
        try {
            const newStatus = rule.status === RuleStatus.Active ? RuleStatus.Inactive : RuleStatus.Active
            await updateRule(rule.id, { status: newStatus })
            message.success(newStatus === RuleStatus.Active ? '规则已启用' : '规则已停用')
            loadData()
        } catch (error) {
            console.error('Failed to toggle status:', error)
            message.error('状态切换失败')
        }
    }

    // 渲染风险等级标签
    function renderRiskBadge(riskLevel: RiskLevel) {
        return (
            <span
                style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                    color: '#fff',
                    backgroundColor: RISK_COLORS[riskLevel] || '#595959',
                }}
            >
                {riskLevel}
            </span>
        )
    }

    // 渲染关联文书类型（带溢出显示）
    function renderDocTypes(rule: ReviewRule) {
        if (rule.is_universal) {
            return (
                <span
                    style={{
                        display: 'inline-block',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        backgroundColor: '#e6f4ff',
                        color: '#1677ff',
                        whiteSpace: 'nowrap',
                    }}
                >
                    通用
                </span>
            )
        }

        const scopeIds = Array.from(new Set([...(rule.type_ids || []), ...(rule.subtype_ids || [])]))
        if (scopeIds.length === 0) {
            return <span style={{ color: '#999' }}>未关联</span>
        }

        const MAX_SHOW = 5  // 最多显示5个标签
        const names = scopeIds.map(id => getScopeName(id))
        const showNames = names.slice(0, MAX_SHOW)
        const remaining = names.length - MAX_SHOW

        return (
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center', flexWrap: 'nowrap' }}>
                {showNames.map((name, i) => (
                    <span
                        key={i}
                        style={{
                            display: 'inline-block',
                            padding: '1px 6px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            backgroundColor: '#e6f4ff',
                            color: '#1677ff',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {name}
                    </span>
                ))}
                {remaining > 0 && (
                    <Tooltip title={names.slice(MAX_SHOW).join('、')}>
                        <span
                            style={{
                                display: 'inline-block',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                fontSize: '12px',
                                backgroundColor: '#f0f0f0',
                                color: '#666',
                                cursor: 'pointer',
                            }}
                        >
                            +{remaining}
                        </span>
                    </Tooltip>
                )}
            </div>
        )
    }

    // 列定义 - 按照用户要求的顺序
    const columns: ColumnsType<ReviewRule> = [
        {
            title: '规则名称',
            dataIndex: 'name',
            key: 'name',
            width: 180,  // 约10个汉字
            ellipsis: true,
            render: (name: string, record: ReviewRule) => (
                <Tooltip title={record.description}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <span
                            className={`status-dot ${record.status === RuleStatus.Active ? 'active' : 'inactive'}`}
                        />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {name}
                        </span>
                    </div>
                </Tooltip>
            ),
        },
        {
            title: '风险等级',
            dataIndex: 'risk_level',
            key: 'risk_level',
            width: 90,
            render: (riskLevel: RiskLevel) => renderRiskBadge(riskLevel),
        },
        {
            title: '关联文书类型',
            key: 'scope',
            // 不设置 width，让它占用剩余空间
            render: (_: unknown, record: ReviewRule) => renderDocTypes(record),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 110,
            showSorterTooltip: false,  // 禁用 "Click to sort" 提示
            render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
        },
        {
            title: '操作',
            key: 'action',
            width: 140,
            render: (_: unknown, record: ReviewRule) => (
                <Space size="small">
                    <Switch
                        size="small"
                        checked={record.status === RuleStatus.Active}
                        onChange={() => handleToggleStatus(record)}
                    />
                    <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEditModal(record)}
                    />
                    <Popconfirm
                        title="删除规则"
                        description="确定要删除这条规则吗？此操作不可恢复。"
                        onConfirm={() => handleDelete(record.id)}
                        okText="确认删除"
                        cancelText="取消"
                        icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
                    >
                        <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                        />
                    </Popconfirm>
                </Space>
            ),
        },
    ]

    if (loading) {
        return (
            <div className="loading-container">
                <Spin size="large" tip="加载中..." />
            </div>
        )
    }

    return (
        <div className="rules-page">
            <div className="page-header">
                <h2>自定义规则库</h2>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
                    新建规则
                </Button>
            </div>

            <Tabs activeKey={activeTab} onChange={setActiveTab}>
                <TabPane tab="适用规则" key={RuleType.Applicable} />
                <TabPane tab="排除规则" key={RuleType.Exclusion} />
            </Tabs>

            <div className="filters">
                <Input
                    placeholder="搜索规则名称或描述..."
                    prefix={<SearchOutlined />}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ width: 240 }}
                    allowClear
                />
                <Select
                    value={statusFilter}
                    onChange={setStatusFilter}
                    style={{ width: 110 }}
                >
                    <Option value="all">全部状态</Option>
                    <Option value={RuleStatus.Active}>已开启</Option>
                    <Option value={RuleStatus.Inactive}>已关闭</Option>
                </Select>
                <Select
                    value={riskFilter}
                    onChange={setRiskFilter}
                    style={{ width: 120 }}
                >
                    <Option value="all">全部风险</Option>
                    <Option value={RiskLevel.High}>高</Option>
                    <Option value={RiskLevel.Medium}>中</Option>
                    <Option value={RiskLevel.Low}>低</Option>
                </Select>
                <Select
                    mode="multiple"
                    value={docTypeFilter}
                    onChange={setDocTypeFilter}
                    style={{ width: 200 }}
                    placeholder="文书类型"
                    allowClear
                    maxTagCount={1}
                    maxTagPlaceholder={(omittedValues) => `+${omittedValues.length}`}
                >
                    {docTypeFilterOptions.map(opt => (
                        <Option key={opt.value} value={opt.value}>
                            {opt.label}
                        </Option>
                    ))}
                </Select>
            </div>

            <Table
                columns={columns}
                dataSource={filteredRules}
                rowKey="id"
                pagination={{ pageSize: 10 }}
                locale={{ emptyText: '暂无规则，点击"新建规则"添加' }}
                tableLayout="fixed"
            />

            {/* Create/Edit Modal */}
            <Modal
                title={editingRule ? '编辑规则' : '新建规则'}
                open={isModalOpen}
                onOk={handleSubmit}
                onCancel={() => setIsModalOpen(false)}
                confirmLoading={submitting}
                okText={editingRule ? '保存' : '创建'}
                cancelText="取消"
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    style={{ marginTop: 24 }}
                >
                    <Form.Item
                        name="name"
                        label="规则名称"
                        rules={[{ required: true, message: '请输入规则名称' }]}
                    >
                        <Input placeholder="请输入规则名称" />
                    </Form.Item>
                    <Form.Item
                        name="description"
                        label="规则描述"
                        rules={[{ required: true, message: '请输入规则描述' }]}
                    >
                        <TextArea rows={3} placeholder="请输入规则描述" />
                    </Form.Item>
                    <Form.Item
                        name="risk_level"
                        label="风险等级"
                        rules={[{ required: true, message: '请选择风险等级' }]}
                    >
                        <Select placeholder="请选择风险等级">
                            <Option value={RiskLevel.High}>
                                <span style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    color: '#fff',
                                    backgroundColor: RISK_COLORS[RiskLevel.High],
                                }}>高</span>
                            </Option>
                            <Option value={RiskLevel.Medium}>
                                <span style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    color: '#fff',
                                    backgroundColor: RISK_COLORS[RiskLevel.Medium],
                                }}>中</span>
                            </Option>
                            <Option value={RiskLevel.Low}>
                                <span style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    color: '#fff',
                                    backgroundColor: RISK_COLORS[RiskLevel.Low],
                                }}>低</span>
                            </Option>
                        </Select>
                    </Form.Item>
                    <Form.Item
                        name="subtype_ids"
                        label="关联文书类型"
                        rules={[{ required: true, message: '请选择关联的文书类型' }]}
                    >
                        <Cascader
                            options={cascaderOptions}
                            multiple
                            placeholder="请选择关联的文书类型"
                            showSearch
                            expandTrigger="hover"
                            onChange={handleCascaderChange as any}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}

export default RulesPage
