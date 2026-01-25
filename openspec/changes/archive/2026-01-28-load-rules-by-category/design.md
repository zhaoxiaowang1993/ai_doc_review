# 设计方案：按分类加载审核规则

## Context

### 现状
- 文档上传时不选择分类，审核时加载所有 `active` 状态的规则
- 存在遗留的 `document_rules` 表，支持按文档启用/禁用规则
- 规则已支持关联文书子类（`rule_subtype_relations` 表），但审核流程未使用此关联

### 约束
- SQLite 单文件数据库，需保持简单查询
- 前端使用 Fluent UI 组件库
- 审核流程通过 `LangChainPipeline` 实现

## Goals / Non-Goals

**Goals:**
- 上传文档时选择文书子类
- 审核时按层级加载规则（子类 → 父类 → 通用）
- 清理遗留的文档-规则直接关联逻辑
- 审核页面展示文档分类标签

**Non-Goals:**
- 不修改 AI 审核引擎内部逻辑（仅修改规则加载方式）
- 不新增文书分类的 CRUD 管理页面（已有）
- 不处理历史已上传文档的分类补录

## Decisions

### Decision 1: 规则层级继承查询策略

**选择**: 单次 SQL 查询联合子类 + 父类 + 通用

```sql
SELECT DISTINCT r.* FROM rules r
JOIN rule_subtype_relations rsr ON r.id = rsr.rule_id
LEFT JOIN document_subtypes ds ON rsr.subtype_id = ds.id
WHERE r.status = 'active'
  AND (
    rsr.subtype_id = ?               -- 子类精确匹配
    OR ds.type_id = ?                -- 父类匹配
    OR rsr.subtype_id = 'universal'  -- 通用规则
  )
```

**替代方案**:
- 分三次查询再合并 → 性能差，代码复杂
- 预计算标记表 → 增加维护成本

**理由**: 单次查询性能最优，SQLite 对小数据集 JOIN 效率高

### Decision 2: 文档分类存储位置

**选择**: 新建 `documents` 表（对象）存储文档元数据

**替代方案**:
- 扩展 `issues` 表 → 耦合度高，文档类型属于文档本身属性而非问题属性
- 存储在文件名或路径中 → 不结构化，难以查询

**理由**: 文档是核心实体，应当有独立的数据表。这支持：
- 持久化文档的元数据（如分类、上传时间、状态）
- **重新审阅能力**: 点击"重新审阅"时，直接读取 `documents.subtype_id`，无需用户再次选择，确保规则一致性
- 未来扩展更多文档属性（如标签、作者等）
- 更清晰的数据模型关系（Document 1:N Issues）

### Decision 3: 前端分类选择器实现

**选择**: 使用 Ant Design Modal + Cascader 组件

**实现细节**:
- 上传按钮点击后 -> 弹出 Ant Design Modal
- Modal 内容: 文件选择区 + 文书分类级联选择器
- 校验: 必须选择文件和分类后，"开始上传"按钮才可用

- 第一级: 文书类型（法律合同、医学文书...）
- 第二级: 文书子类（劳动合同、租赁合同...）

**理由**: 用户对分类层级有清晰认知，级联选择符合心智模型

### Decision 4: 遗留代码清理策略

**选择**: 一次性删除，不做兼容

| 删除项 | 位置 |
|--------|------|
| `document_rules` 表 | `db_client.py` |
| `DocumentRuleAssociation` 模型 | `common/models.py` |
| `get_document_rules` / `set_document_rule` | Repository/Service/Router |
| 前端相关代码 | `RulesPanel.tsx`, `api.ts`, `rule.ts` |

**理由**: 该功能使用率低，且与新逻辑冲突，保留会增加混乱

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 历史文档无分类，审核时无法加载规则 | 前端强制选择分类后才能审核；API 层 subtype_id 参数必填 |
| 删除 `document_rules` 表导致数据丢失 | 该表数据无业务价值（仅存储临时开关状态），可直接删除 |
| 规则未关联任何子类时不会被加载 | 规则创建时默认关联"通用"；规则列表提示未关联分类的规则 |

## Migration Plan

1. **数据库迁移**: 
   - 新建 `documents` 表 (id, filename, subtype_id, created_at, ...)
   - 删除 `document_rules` 表
   - (可选) 迁移现有 `issues` 所属的文档到 `documents` 表（如果需要保留历史关联）

2. **后端部署**: 更新 API，`subtype_id` 参数对新审核必填

3. **前端发布**: 同步更新上传和审核页面

4. **回滚策略**: 恢复旧代码即可，无数据依赖

## Open Questions

- [已决定] 历史文档如何处理？→ 不处理，新审核时强制选择分类
