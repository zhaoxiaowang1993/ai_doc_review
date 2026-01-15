## 现象结论（已定位）
- 线上与本地差异的根因是“两个全局 body 样式源在打架”，且 dev 与 build 后的 CSS 注入/抽取顺序可能不同。
- Landing 在 [landing.css](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/pages/landing/landing.css#L15-L21) 里直接写了 `body { background-color; color; }`；而全局主题背景在 [index.css](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/index.css#L17-L26) 里写了 `body[data-theme] { background: ... }` 以及 [index.css](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/index.css#L28-L50) 的 `body::before` 网格层。
- 两边都改“全局 body”，谁的规则在最终产物里靠后、谁就赢；因此会出现：线上背景/文字色与本地不一致。

## 修复原则（让结果不依赖 CSS 顺序）
- 不再依赖“CSS 加载顺序”，改成“确定性的选择器优先级 + 显式页面标记”。
- Landing 页面挂载时给 `body` 打标（例如 `data-page="landing"`），卸载时恢复。
- 全局 theme 背景/网格只在非 landing 页面生效；landing 页面则强制使用 landing 自己的背景与文字色。

## 具体改动方案（最小侵入、可回滚）
1) 在 [LandingPage.tsx](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/pages/landing/LandingPage.tsx) 增加一个 `useEffect`：
- mount：`document.body.setAttribute('data-page', 'landing')`
- unmount：恢复之前的 `data-page`（若原本没有则 removeAttribute）。

2) 调整 [index.css](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/index.css) 的全局背景与网格规则：
- 给 `body[data-theme='dark']` / `body[data-theme='light']` / `body::before` 等选择器追加 `:not([data-page='landing'])`，确保 landing 时全局背景与网格不生效。

3) 调整 [landing.css](file:///Users/zhaochengwang/Documents/yinyutech/DocReview/ai-document-review/app/ui/src/pages/landing/landing.css) 的 `body` 规则，使其在 landing 时“必胜”：
- 用更高确定性的选择器，例如 `body[data-theme][data-page='landing'] { background-color: var(--lp-bg); color: var(--lp-text); }`
- 同时关闭网格层：`body[data-theme][data-page='landing']::before { display: none; }`（或等效方式）。

## 验证方式（必须过）
- 本地开发：进入 Landing，确认 computed style：`body` 背景为 `--lp-bg`，且文字继承为白色；切换主题不影响 Landing。
- 生产构建：`vite build` 后用同样的静态托管方式预览（与线上一致），确认背景与文字色一致。
- 回归检查：非 Landing 页面仍保持原先的主题渐变背景与网格。

## 可选的长期优化（不作为本次必需）
- 彻底禁止页面级 CSS 修改 `body`：把 Landing 的背景/文字色迁移到 `.lp-container`（或单独 Layout），从根上消除“全局互相覆盖”的坏味道。

（说明：当前可用技能里只有 skill-creator，属于“创建新技能”的工具，不适用于排查/修复样式问题，因此我没有启用技能工具。）