# 跨系统交接：先读这里

最新接手请先读 [CURRENT_STATE.md](CURRENT_STATE.md)，将 [AGENT_START.md](AGENT_START.md) 复制给接手 agent。下文是历史交接快照的说明和安装指导；旧 ZIP、128/59 测试数量及“六次迁移”不代表当前源码。当前双例对比源码待集成验收，状态以 CURRENT_STATE 为准。

日期：2026-10-01。用户已明确恢复开发，完整目标状态为active。本文件及ZIP保留交接历史；ZIP不代表恢复后最新源码。

## 包内与当前状态

这是独立新版源码，包含前端/API、生成契约、六次迁移、锁文件、测试、Docker配置及全部需求/架构文档。ZIP另外包含本线程HANDOFF.md、SOURCE_COMMIT.txt及逐文件SHA-256的MANIFEST.json。不包含旧Windows应用、.git历史、依赖缓存、数据库、账号凭据、私人附件、实际.env或模型密钥。首次运行须联网安装依赖，不搬运Windows的node_modules或.venv。

已实现学习会话/计时/历史、五方法/九情境、反馈/文字题目/作答更正、每日金句与偏好、章节/知识点/归档恢复、题目关联、五级用户自评与可追溯证据。完整产品尚未完成。

## 本机启动（Windows / Linux / macOS）

需要Node24、pnpm11.19.0、Python3.12+、uv。进入解压后的hermes-rebuild：

```sh
pnpm install --frozen-lockfile
pnpm --dir apps/web install --frozen-lockfile
uv sync --project apps/api --frozen
pnpm contracts:check
```

API终端：

```sh
cd apps/api
uv run --frozen python -m hermes_api.cli migrate
uv run --frozen python -m hermes_api.cli bootstrap --username YOUR_USERNAME
uv run --frozen uvicorn hermes_api.main:app --host 127.0.0.1 --port 8000
```

bootstrap会提示输入至少12字符的新密码，不覆盖已有账户。默认新建apps/api/hermes-development.db，仅用于开发，不能指向生产数据。另开终端在hermes-rebuild执行`pnpm dev:web`，打开http://127.0.0.1:5173。代理转发到API8000；如更改端口，同时改Vite代理及API的HERMES_ALLOWED_ORIGIN，不终止未知占用进程。

Docker/PostgreSQL组合路径见README，当前未实测Docker/PostgreSQL。公开部署另需TLS、安全cookie及生产配置；本机启动不等于上线验证。

## 实际验证与剩余项

交接复核：API目录`uv run --frozen --offline --cache-dir .uv-cache pytest -q`，128 passed、1条既有Starlette/httpx警告；同环境`ruff check src tests migrations`及`ruff format --check src tests migrations`，PASS，46文件格式通过。web目录`pnpm test`为59项/15文件；`pnpm typecheck`和`pnpm build`通过。根目录`pnpm contracts:check`通过。本机使用UV_NO_SYNC=1；新系统先安装依赖。首次安装不能要求离线完成。

真实页面已验证章节→知识点→无证据自评→学习→反馈建题→题目关联→带依据自评→作答更正后stale且原等级保留→章节归档禁用/恢复。已修正反馈建题学科丢失、错误类别英文和十类零值空态，均有回归测试。五视口做过DOM布局检查及桌面截图查看；截图未保存为文件。

暂停前最后已重启隔离API，但重启后的浏览器刷新/读回复核尚未完成，不能计完整持久性链路PASS。跨操作系统实跑、物理平板、完整视觉、PostgreSQL及生产备份恢复为NOT COVERED；没有公开发布或真实模型调用。

若用户恢复目标，先读08最终架构、10完整实施跟踪、17本批记录、06验收矩阵；在新系统运行检查，完成最终重启/跨设备读回，再继续私有附件/图片/PDF指定页、卡点、复习/建议、双例对比、收尾/七日节奏、七区首页、噜噜与顾问。57项原需求及补充验收保持完整，不能把当前快照当成全产品完成。

保留AGENTS.md的提交、补测、隔离数据和诚实报告要求。SOURCE_COMMIT.txt用于追溯；若需独立Git仓库，在解压目录`git init`并提交导入快照。包旁边的.sha256验证ZIP，MANIFEST.json验证每个文件。
