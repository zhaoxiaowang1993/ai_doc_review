# 实现任务清单：按分类加载审核规则

## 1. 数据库迁移与模型

- [x] 1.1 `db_client.py`: 添加 `documents` 表创建语句 (id, filename, subtype_id, created_at)
- [x] 1.2 `db_client.py`: 添加初始化/迁移逻辑（创建 documents 表）
- [x] 1.3 `db_client.py`: 删除 `document_rules` 表相关代码
- [x] 1.4 `common/models.py`: 新增 `Document` 模型类
- [x] 1.5 `common/models.py`: 删除 `DocumentRuleAssociation` 类

## 2. 后端文档管理能力 (新增)

- [x] 2.1 创建 `database/documents_repository.py`: 实现文档 CRUD (create, get_by_id)
- [x] 2.2 创建 `services/documents_service.py`: 封装文档业务逻辑
- [x] 2.3 `dependencies.py`: 注册 `DocumentsService` 依赖

## 3. 后端 API 适配

- [x] 3.1 修改 `routers/files.py`: 上传接口在保存文件后，创建 `Document` 记录 (存入 subtype_id)
  - 需注入 `DocumentsService`
- [x] 3.2 使用 `routers/issues_router.py` 中的 `re_review` 接口逻辑适配：
  - 读取文档 `subtype_id`
  - 调用 `get_rules_for_review(subtype_id)`
  - 将规则传入 `LangChainPipeline`
- [x] 3.3 `routers/rules.py`: 删除旧的 `get_document_rules` / `set_document_rule` 端点

## 4. 后端规则加载能力

- [x] 4.1 `rules_repository.py`: 实现 `get_rules_for_review(subtype_id)` (多级加载)
- [x] 4.2 `rules_service.py`: 添加对应服务方法
- [x] 4.3 `routers/rules.py`: 添加 `/api/v1/rules/for-review/{subtype_id}` 端点 (供前端展示参考)

## 5. 后端遗留清理

- [x] 5.1 删除 `rules_repository.py` 中的 `get_document_rules`
- [x] 5.2 删除 `rules_service.py` 中的 `get_document_rules`

## 6. 前端类型和 API 适配

- [x] 6.1 `types/index.ts` (或 rule.ts): 新增 `Document` 接口，删除 `DocumentRuleAssociation`
- [x] 6.2 `services/api.ts`: 修改 `uploadFile` 支持传递 `subtypeId`
- [x] 6.3 `services/api.ts`: 新增 `getDocument(docId)` 接口
- [x] 6.4 `services/api.ts`: 删除旧规则关联接口

## 7. 前端上传与分类

- [x] 7.1 创建 `DocumentCategorySelector` 组件
- [x] 7.2 创建 `UploadModal` 组件 (Ant Design Modal)
  - 包含文件选择 (Dragger)
  - 包含 `DocumentCategorySelector` (Cascader)
  - 确定按钮提交 (uploadFile api)
- [x] 7.3 修改主页/列表页的"上传"按钮，点击唤起 `UploadModal`
- [ ] 7.4 (可选) 文件列表页：展示文档分类信息

## 8. 前端审核页面适配

- [x] 8.1 审核页面加载时，调用 `getDocument(docId)` 获取元数据
- [x] 8.2 页面顶部展示文档分类标签
- [x] 8.3 移除旧的 RulesPanel 文档关联逻辑，改为仅展示"当前应用规则"

## 9. 测试验证

- [ ] 9.1 验证文档上传后 `documents` 表有记录且 `subtype_id` 正确
- [ ] 9.2 验证重审逻辑：点击重审 -> 自动加载分类规则 -> 结果一致
- [ ] 9.3 验证规则生效：创建一条特定子类规则，上传该类文档，验证 Issue 是否生成

