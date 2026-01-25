# category-aware-review Specification

## Purpose
按分类加载审核规则的核心能力，实现规则与文书分类的智能匹配。

## ADDED Requirements

### Requirement: 按分类加载审核规则
系统 SHALL 根据文书子类加载匹配的审核规则，支持层级继承。

#### Scenario: 加载子类关联规则
- **WHEN** 审核一份"劳动合同"文书
- **THEN** 系统加载所有关联了"劳动合同"子类的规则

#### Scenario: 加载父类关联规则
- **WHEN** 审核一份"劳动合同"文书
- **THEN** 系统同时加载所有关联了"法律合同"父类的规则

#### Scenario: 加载通用规则
- **WHEN** 审核任意文书
- **THEN** 系统同时加载所有关联了"通用"（universal）的规则

#### Scenario: 仅加载启用状态规则
- **WHEN** 加载规则时
- **THEN** 仅返回 `status = 'active'` 的规则

### Requirement: 规则类型区分应用
系统 SHALL 区分适用规则和排除规则的应用逻辑。

#### Scenario: 适用规则触发风险
- **WHEN** 文书片段违反"适用规则"
- **THEN** 系统标记该片段为风险项

#### Scenario: 排除规则豁免判定
- **WHEN** 文书片段违反"适用规则"但同时命中"排除规则"
- **THEN** 系统不标记该片段为风险项（视为合规）

### Requirement: 文档分类必选
系统 SHALL 要求用户在审核前选择文书分类。

#### Scenario: 审核前选择分类
- **WHEN** 用户发起文书审核
- **THEN** 系统要求用户选择文书子类后才能继续

#### Scenario: 重新审阅
- **WHEN** 用户对已审阅文档点击"重新审阅"
- **THEN** 系统自动读取该文档已存储的分类信息
- **AND** 使用该分类重新加载当前最新的规则进行审核
- **AND** 确保新筛选的规则被正确应用到 AI 审核工作流中

#### Scenario: API 校验分类参数
- **WHEN** 调用审核 API 时未提供 `subtype_id` 且无法从文档元数据获取
- **THEN** 系统返回 400 错误，提示缺失分类信息
