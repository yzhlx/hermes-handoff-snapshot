# Hermes web

独立 React 客户端，开发时通过 Vite 将 `/api` 转发至 `127.0.0.1:8000`。

```powershell
pnpm install --frozen-lockfile
pnpm dev
pnpm typecheck
pnpm test
pnpm build
```

当前实现：登录、退出、服务状态、学科选择与自由学习；学习现场支持开始、暂停、继续、结束和二次确认取消；可选计时按服务端返回的有效时段展示。学习方法从服务端目录读取，开始时把方法 ID 单独保存到学习现场。学习记录单独分页显示，可读取会话详情、状态和计时片段，不根据会话或时长推断掌握情况。领域类型来自 `packages/contracts/src/schema.d.ts` 的 OpenAPI 生成结果。

计时可能包含设备休眠或断线时间，当前界面会明确提示，但还不支持手动校正异常时段。

## 界面层结构（设计令牌 / 外壳 / 数据驱动导航）

- `src/shared/ui/tokens.css`：唯一的设计令牌来源（颜色、间距、圆角、字号、阴影、动效、布局、层级）。新代码只引用语义令牌（`--bg-*` / `--text-*` / `--border-*` / `--accent-*`）；`--canvas` / `--panel` / `--ink` / `--muted` / `--border` / `--sage` / `--radius` / `--card` 是留给尚未迁移页面的兼容别名。
- `src/app/AppShell.tsx` + `src/shared/ui/shell.css`：外壳（顶栏 / 侧边导航 / 内容列），不持有业务状态；页面内容通过 children 传入，外壳级提示走 `banner`。
- `src/app/navigation.ts`：数据驱动导航（页面 id、标签、图标、详情页归属）。新增入口 = 在这里加一条记录，外壳按数据渲染；标签同时是按钮可访问名称与顶栏面包屑标题。
- `src/shared/ui/icons.tsx`：只包含外壳所需的最少线性图标，全部 `aria-hidden`，不参与可访问名称计算。
- 引用顺序：`src/main.tsx` 依次导入 tokens → shell → styles。

配色取自参考图采样与 AGENTS.md §7.4 色板，实测对比度记录在 `tokens.css` 顶部注释；断点约定为 390 / 600 / 768 / 1024 / 1366。

服务端状态由 TanStack Query 管理；未提交草稿与不确定命令的幂等键仅保存在按用户 ID 绑定的内存中。同账号登录过期后重新登录可恢复；主动退出、换账号、整页重载会清除。浏览器不保存密码或 CSRF token 到持久化存储。

基础工程使用确定性 Agent 模拟，不包含真实模型对话、错题工作流与公共云部署；这些限制保留在工程文档中。
