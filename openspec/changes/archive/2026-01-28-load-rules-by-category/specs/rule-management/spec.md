# rule-management Delta Specification

## ADDED Requirements

### Requirement: 按子类及父类加载规则
系统 SHALL 支持按文书子类加载规则，并自动包含父类和通用规则。

#### Scenario: 层级继承查询
- **WHEN** 请求获取子类 "subtype_labor_contract" 的规则
- **THEN** 返回关联了以下任意一项的活动规则：
  - 子类 "subtype_labor_contract"
  - 父类 "type_legal"
  - 通用 "universal"

### Requirement: 规则未关联分类提示
系统 SHALL 在规则列表中提示未关联任何分类的规则。

#### Scenario: 展示未关联提示
- **WHEN** 规则未关联任何文书子类且未标记为通用
- **THEN** 规则列表中该规则显示警告标识："未关联分类，将不会被任何审核加载"

## REMOVED Requirements

### Requirement: 文档-规则直接关联
**Reason**: 与新的"规则关联文书分类"逻辑冲突，功能被完全取代
**Migration**: 删除 `document_rules` 表，移除相关 API 和 UI。用户通过规则关联分类来控制规则适用范围。

原文：
> 系统支持按文档启用/禁用特定规则。
> - GET /api/v1/rules/documents/{doc_id} 获取文档规则关联
> - PUT /api/v1/rules/documents/{doc_id}/{rule_id} 设置文档规则状态
