# Proposal: 文书审核时按分类加载规则

## Why

当前文书审核时加载所有活动状态的自定义规则，无论规则是否与当前文书类型匹配。这导致：
- 不相关的规则被应用到文书上，可能产生误报
- 无法发挥规则与文书分类关联的能力
- 用户需要手动管理哪些规则应用于哪些文书

此外，**存在遗留的"文档直接关联规则"逻辑需要清理**：
- 数据库表 `document_rules`（doc_id → rule_id）允许每个文档单独启用/禁用规则
- 此设计与新的"规则关联文书分类"逻辑冲突
- 应迁移到基于分类的规则关联模式

## What Changes

### 核心功能
1. **文档上传流程**：用户上传文档时需要选择文书子类（subtype）
2. **审核规则加载逻辑**：
   - 加载关联了当前文书子类的规则
   - 加载关联了当前文书子类所属父类（type）的规则
   - 加载关联了"通用"（universal）场景的规则
   - 仅加载状态为"启用"的规则
3. **审核页面展示**：展示当前文档所属的分类标签
4. **规则应用逻辑**：适用规则用于风险标识，排除规则用于豁免判定

### 遗留逻辑清理 (BREAKING)
1. **弃用 `document_rules` 表**：删除文档-规则直接关联表
2. **弃用 `DocumentRuleAssociation` 模型**：从 `common/models.py` 移除
3. **弃用相关 API**：
   - `GET /api/v1/rules/documents/{doc_id}` → 删除
   - `PUT /api/v1/rules/documents/{doc_id}/{rule_id}` → 删除
4. **重构 `RulesPanel.tsx`**：移除按文档启用/禁用规则的 UI 逻辑
5. **数据迁移**：现有 `document_rules` 数据无需迁移（该表功能被分类关联完全取代）

## Capabilities

### New Capabilities
- `category-aware-review`: 按分类加载审核规则的核心逻辑，包括规则匹配、层级继承和通用规则合并

### Modified Capabilities
- `document-category`: 新增需求：上传文档时选择分类，审核页面展示分类标签，**数据存储在 Document 对象中**
- `rule-management`: 新增需求：支持按子类及其父类加载规则，支持层级继承查询；**删除文档-规则直接关联能力**

## Impact

### 后端 API
| 文件 | 变更 |
|------|------|
| `routers/files.py` | 文件上传 API 新增 `subtype_id` 参数 |
| `routers/issues.py` | 审核 API 需从 `documents` 表获取分类 |
| `routers/rules.py` | **删除** `get_document_rules` 和 `set_document_rule` 端点 |
| `services/rules_service.py` | 新增 `get_rules_for_review()` 方法，**删除** `get_document_rules()` |
| `services/documents_service.py` | **新增** 文档管理服务 (Create, Get) |
| `database/rules_repository.py` | 扩展规则查询逻辑，**删除** `get_document_rules()` |
| `database/documents_repository.py` | **新增** 文档数据访问层 |
| `database/db_client.py` | **新增** `CREATE_DOCUMENTS_TABLE`, **删除** `CREATE_DOCUMENT_RULES_TABLE` |

### 前端 UI
| 文件 | 变更 |
|------|------|
| `components/RulesPanel.tsx` | **重构**：移除 `docId`、`enabledRuleIds`、`onEnabledRulesChange` props，移除 `getDocumentRules`/`setDocumentRule` 调用 |
| `services/api.ts` | **删除** `getDocumentRules()` 和 `setDocumentRule()` |
| `types/rule.ts` | **删除** `DocumentRuleAssociation` 接口 |
| 文件上传组件 | 新增分类选择器 |
| 审核页面 | 展示文档分类标签 |

### 数据模型
| 模型 | 变更 |
|------|------|
| `common/models.py` | **删除** `DocumentRuleAssociation` 类，**新增** `Document` 类 |

### 数据流变更
```
当前：上传文档 → get_active_rules() → 应用所有活动规则
                ↓
           document_rules 表覆盖启用状态（遗留逻辑）

变更后：上传文档(含分类) → get_rules_for_review(subtype_id) → 应用匹配规则
```
