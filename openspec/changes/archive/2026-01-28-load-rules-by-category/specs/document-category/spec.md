# document-category Delta Specification

## ADDED Requirements

### Requirement: 上传文档时选择分类
用户 SHALL 在上传文档后选择文书分类。

#### Scenario: 上传后选择分类
- **WHEN** 用户上传一份 PDF 文档
- **THEN** 系统弹出 Ant Design 风格的模态框（Modal）
- **AND** 用户在模态框中选择文件并指定文书分类（级联选择）
- **AND** 用户确认后开始上传
- **AND** 系统 SHALL 将分类信息持久化存储在 Document 对象中

### Requirement: 审核页面展示分类标签
系统 SHALL 在审核页面展示当前文档所属的分类。

#### Scenario: 展示分类标签
- **WHEN** 用户进入文档审核页面
- **THEN** 页面顶部展示文档所属的分类标签（如："法律合同 > 劳动合同"）
- **AND** 此分类信息仅作展示，不可在详情页直接编辑
