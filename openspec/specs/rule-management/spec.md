# rule-management Specification

## Purpose
TBD - created by archiving change add-rule-library. Update Purpose after archive.
## Requirements
### Requirement: 规则基本属性
每条规则 SHALL 具备唯一标识、名称、描述、风险等级及状态。
#### Scenario: 自动分配字段
- **Given** 用户新建一条规则
- **Then** 系统应自动生成“规则序号”和“创建时间”
- **And** 这两个字段在编辑时不可修改

### Requirement: 规则分类逻辑
规则 SHALL 分为“适用规则”与“排除规则”，并区分来源。
#### Scenario: 规则类型区分
- **Given** AI 执行文档审核
- **When** 遇到“适用规则”时，违反项应被标识
- **But When** 命中“排除规则”时，应豁免对应的规则判定

### Requirement: 规则关联能力
规则 SHALL 能灵活关联到一个或多个文书分类。
#### Scenario: 多选子类关联
- **When** 创建规则时
- **Then** 用户应能通过级联多选框选择一个或多个文书子类
- **And** 如果选择了特殊的“通用”选项，则该规则适用于所有文书

### Requirement: 规则检索与搜索
列表页 SHALL 支持多维度过滤与搜索。
#### Scenario: 列表搜索与过滤
- **Given** 规则列表页面
- **Then** 支持按规则名称或描述进行模糊搜索
- **And** 支持按状态（开启/关闭）、风险等级（高/中/低）及关联子类进行精确过滤

### Requirement: 排序逻辑
列表 SHALL 支持按照时间戳进行排序。
#### Scenario: 时间排序
- **When** 用户点击创建时间表头
- **Then** 列表应支持按创建时间进行正序或倒序排列

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
- **THEN** 规则列表中该规则显示警告标识：「未关联分类，将不会被任何审核加载」

