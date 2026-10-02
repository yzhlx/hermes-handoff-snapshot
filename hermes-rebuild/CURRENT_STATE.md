# 最小接手状态

快照日期：2026-10-02（Asia/Shanghai，延续 10-01 任务）。状态：完整产品未完成；双例对比（25）、可选 AI 顾问（26）、独立卡点状态流（27）、计时异常校正（28）与数据主权（29）五批已实现并验证。下一批优先合并 09 顾问 stub，再账号恢复/完整冲突展示，最后全矩阵审计。GitHub 交接分支 `codex/handoff-current-20261001`；没有宣布暂停或结束完整目标。

## 目标与边界

实现原始需求 FR-001—FR-057 及 AC-X01—AC-X17 全部第一版功能。产品是云端个人考研数字书房；用户自主选学什么，建议可忽略，不产生欠债，不将看答案视为掌握。

新版代码仅在本目录。React/TypeScript/Vite 前端独立运行；FastAPI/Pydantic API；业务领域→端口→SQLAlchemy 适配器，Alembic 显式迁移；生产目标 PostgreSQL，SQLite 用于开发和隔离测试；模型 Mock + 可替换端口。架构以 08 为准，不继承旧应用 Windows-only 边界。遵守本目录 AGENTS.md。

## 当前源码与验证

- 原开发分支 `work/local-setup`；交接分支 `codex/handoff-current-20261001`。交接文档提交 `f06d6fb`，最近已验收实现 `2fba27d`（七区首页）。基础/会话计时/反馈题目金句/章节知识证据/私有附件指定页/建议复习记录收尾/七区首页/双例对比/可选 AI 顾问/独立卡点状态流/计时异常校正/数据主权已经分批实现；证据见 09、12、15、17、19、21、23、25、26、27、28、29。不是完整产品交付。当前检查点哈希请执行 `git rev-parse HEAD`。
- **双例对比已验收**：后端 `comparison_{domain,ports,service,storage,schemas,routes}.py`、迁移 `0010_problem_comparisons.py`；前端 `features/comparisons/`（含新增 `ProblemAnswerCheck.tsx`）与抽离复用的 `features/feedback/AttemptCorrection.tsx`。本批修复了"查看与核对原作答"断裂入口（原只打开只读详情），交付与证据见 25。源码随交接分支提交。
- 对比规则：两个不同的本人题目，可选各自对应作答；七维笔记和结论至少一项非空；原事实独立；归档可恢复；所有者隔离、CSRF、幂等键、If-Match；源版本变化显示 stale，不升级掌握。具体契约见 24。
- **可选 AI 顾问已实现并验证（FR-043—046）**：后端 `advisor_{domain,ports,schemas,mock,service,storage,routes}.py`、迁移 `0011_advisor_runs.py`；前端 `features/advisor/`（`AdvisorPage.tsx`）。`facts` 由本人记录确定性产生（不经模型），`inferences` 经服务端校验（引用存在且属本人、可校验版本、长度、越权语言），`missing_information` 走同一闸门。模型不可用/异常降级为 `degraded`，策略违规 `blocked`，两者都保留记录事实且不发布未校验文本；对学习事实零写入。契约见 04，交付与证据见 26。
- **本批（AI 顾问）执行结果**：API `pytest -q --basetemp=.pytest-run1`：**269 passed、2 failed、2 warnings**（2 项为 Windows 符号链接环境问题）；ruff check 与 format --check PASS；`test_orm_matches_migration_schema` PASS。Web typecheck PASS、build PASS、`pnpm test` **122 passed / 3 failed**（3 项为 jsdom `Blob.stream` 环境问题）。顾问特性 Web 7/7。契约重新生成（55 paths）。
- **本批（AI 顾问）实际应用验证**：全新隔离 QA 库 `.qa-advisor.db` 迁移至 0011（29 表）。真实 HTTP 端到端 **54/54**；**服务重启读回 14/14**；真实 Chromium + 五视口 1440×900、1366×768、1024×768、768×1024、390×844 共 **35/35**，无控制台错误。截图在 `.workbuddy/qa-evidence/advisor/`；QA 脚本与库在 `.local/qa/`。
- **独立卡点状态流已实现并验证（FR-030/036）**：后端 `stuck_point_{domain,ports,schemas,service,storage,routes}.py`、迁移 `0012_stuck_points.py`；前端 `features/stuck-points/`（`StuckPointsPage.tsx`、`draft-store.ts`），App 新增「卡壳点」页与导航。卡壳点是独立记录（不再只是 attempt/reflection 上的自由文本），`open/resolved` 生命周期、`resolved_at`、`resolution_note`；来源作答唯一（部分唯一索引 + 服务层 409 `ALREADY_LINKED`）；从不写入题目/作答/掌握事实。契约见 03，交付与证据见 27。
- **本批（卡点）执行结果**：API `pytest -q --basetemp=.pytest-full1`：**284 passed、2 failed、2 warnings**（2 项为既有 Windows 符号链接环境问题）；ruff check 与 format --check PASS（116 files）；`test_orm_matches_migration_schema` PASS。Web typecheck PASS、build PASS、`pnpm test` **129 passed / 3 failed**（3 项为既有 jsdom `Blob.stream` 环境问题）。契约重新生成（57 paths，纯增量 +776/-0）。同时修复上一批次遗留的 `tests/test_advisor_api.py` 单行超长格式违规（纯空白、零行为变化）。
- **本批（卡点）实际应用验证**：全新隔离 QA 库 `.qa-stuck.db` 迁移至 0012（30 表），两个账号。真实 HTTP 端到端 **40/40**；**服务重启读回 7/7**；真实 Chromium + 五视口 1440×900、1366×768、1024×768、768×1024、390×844 共 **27/27**（含浏览器内真实 resolve→reopen 生命周期），除 favicon 与未登录初始 401 外无控制台错误。截图在 `.workbuddy/qa-evidence/stuck-points/`；QA 脚本与库在 `.local/qa/`。
- **计时异常校正已实现并验证（03 §3 / FR-026/049）**：迁移 `0013_time_segment_corrections.py` 为 `session_time_segments` 增加 `excluded_at`、`original_ended_at`、`correction_note`；新增纯规则 `timing_domain.py`（`MAX_SEGMENT_SECONDS=4h`、`excessive_span`、`crosses_local_day`）与端点 `PATCH /learning-sessions/{id}/time-segments/{segment_id}`。会话负载新增 `timing_review_required` 与片段的 `anomalies`/`review_required`/`excluded`。**校正只允许缩短或排除，不能延长或指向未来**；修正前的结束时间保留；排除的片段不计入 `effective_duration_seconds`；校正推进 session 版本并需要 `If-Match`。前端在「学习记录」提供校正界面，学习现场保留极简（FR-026）并提示异常。交付与证据见 28。
- **本批（计时）执行结果**：API `pytest -q --basetemp=.pytest-full3`：**301 passed、2 failed、2 warnings**（2 项为既有 Windows 符号链接环境问题）；ruff check 与 format --check PASS（120 files）。Web typecheck PASS、build PASS、`pnpm test` **135 passed / 3 failed**（3 项为既有 jsdom `Blob.stream` 环境问题）。契约重新生成（58 paths，纯增量 +252/-0）。
- **本批（计时）实际应用验证**：全新隔离 QA 库 `.qa-timing.db` 迁移至 0013（30 表），两个账号。真实 HTTP 端到端 **25/25**（隔夜跨度标注、缩短、排除/恢复、拒延长与未来、缺 `If-Match` 428、过期 409、幂等重放、跨账号 404、会话自身事实不变）；**服务重启读回 6/6**；真实 Chromium + 五视口 1440×900、1366×768、1024×768、768×1024、390×844 共 **29/29**（含浏览器内真实排除/恢复），除 favicon 与未登录初始 401 外无控制台错误。截图在 `.workbuddy/qa-evidence/timing/`；QA 脚本与库在 `.local/qa/`。
- **数据主权已实现并验证（03 §9 / FR-053）**：迁移 `0014_account_sovereignty.py`（`users.status` + `account_exports` + `account_deletions`，共 32 表）；新增 `account_{domain,ports,schemas,service,storage,routes}.py`。导出为结构化 JSON（含数据字典与带 sha256 的附件清单），私有短期下载、到期 410，**不含密码/登录凭据/存储内部标识，不含他人数据**。删除为两段式：逐字确认登记 → `deletion_pending` 且学习写入 403（账号级端点仍可导出/撤销）→ 撤销回 `active`；再次逐字确认后按子表优先清除全部 owner 行并保留最少墓碑、凭据作废。前端新增顶栏「账号与数据」页。交付与证据见 29。
- **本批（数据主权）执行结果**：完整 API `pytest -q --basetemp=.pytest-full7`：**311 passed、2 failed、2 warnings**（2 项为既有 Windows 符号链接环境问题）；`tests/test_account_sovereignty_api.py` **7/7**（含日期序列化回归）；ruff check 与 format --check PASS（128 files）；Web typecheck PASS、build PASS、`pnpm test` **140 passed / 3 failed**（3 项为既有 jsdom `Blob.stream` 环境问题）；契约重新生成（64 paths，纯增量 +1242/-0）。
- **本批（数据主权）实际应用验证**：全新隔离 QA 库 `.qa-account.db` 迁移至 0014（32 表），两个账号。真实 HTTP 端到端 **33/33**（计数隔离、导出内容与密钥排除、幂等与过期 410、确认短语、待删除封锁写入但可导出可撤销、清除后墓碑与凭据作废、他人数据完整）；**服务重启读回 5/5**；真实 Chromium + 五视口 1440×900、1366×768、1024×768、768×1024、390×844 共 **31/31**（含浏览器内真实生成导出并下载 JSON 文件）。截图在 `.workbuddy/qa-evidence/account/`；QA 脚本与库在 `.local/qa/`。
- **本批（数据主权）真实浏览器验证抓到并修复了一个 500**：`daily_quotes.local_date` 是 `Date` 类型，导出序列化只处理 `datetime`，首次在浏览器点"生成导出包"即 500。单元测试没抓到（测试账号无金句记录）。已修复并补端到端回归用例。
- 上批（卡点）执行结果：API 284 passed / 2 failed；Web 129 passed / 3 failed；隔离 QA 库 40/40 真实 HTTP、重启读回 7/7、五视口 27/27。截图在 `.workbuddy/qa-evidence/stuck-points/`。
- 上批（双例对比）执行结果：API 229 passed / 2 skipped；Web 115 passed / 3 failed；隔离 QA 库 28 项真实 HTTP、重启读回 20/20、五视口 37/37。截图在 `.workbuddy/qa-evidence/comparison/`。
- **NOT COVERED**：生产 PostgreSQL/S3、实际电脑与平板互通、公开部署、生产数据迁移、**真实模型调用（本批只提供确定性 Provider，`privacy.external` 恒为 false，接入需另行授权）**、生产备份恢复。对比页只能核对已存在作答，不能新建作答（`session_id` 必填约束）。0010/0011 已应用于本机隔离 QA 库，不能当成生产迁移。
- **KNOWN LIMITATION（顾问）**：09 批次的进程内 stub（`application.AdvisorService` + `model.MockModel`）与本批产品切片并存；合并需改写 09 既有测试，登记为后续项。`cancel` 在当前同步适配器下是标记取消而非中断在途调用。越权语言为模式匹配（已做 NFKC 归一化与去标点），属纵深防御的一层，非唯一保障。

## 接手后的首个任务

双例对比（25）、可选 AI 顾问（26）、独立卡点状态流（27）、计时异常校正（28）与数据主权（29）五批均已完成并验证。下一批优先**合并 09 顾问 stub**，再账号恢复/完整冲突展示，最后做全矩阵审计（FR-001—057 与 AC-X01—X17）；实现范围仍以需求矩阵为准。

原首任务清单（已完成，保留备查）：

1. 查看 diff 和新文件，复查冻结重试、冲突保留输入、跨账号隔离、只读原附件、原事实不改。`ProblemQuickActions` 的“查看与核对原作答”目前打开只读详情，未连接实际核对编辑入口：应实现明确入口或修正文案，并补回归。
2. 补 App 的“题目与对比”导航、双例方法入口和学习验证时答案默认收起的集成测试；新增只读附件测试已在工作树。检查源版本提示和恢复归档。
3. 执行下列检查；关键比较测试最终版本连跑三次。失败后修复并保留证据。
4. 新建隔离 QA DB/账号，完成比较保存、重新打开、服务重启读回、归档/恢复；确认旧题目、作答、代表题事实只有明确操作才改变。五视口 1440×900、1366×768、1024×768、768×1024、390×844。
5. 写 `25-双例对比交付.md`，更新 03/10/README 的实际状态，提交本批实现。之后优先独立卡点状态流，再受控 AI 顾问、计时校正、导出/删除及全矩阵审计；实现范围仍以需求矩阵为准。

## 命令（相对本目录）

环境 Node24、pnpm11.19.0、Python3.12+、uv。新系统先安装依赖，不能搬运 Windows node_modules/.venv。

```sh
pnpm install --frozen-lockfile
pnpm --dir apps/web install --frozen-lockfile
uv sync --project apps/api --frozen
uv run --project apps/api --frozen pytest apps/api/tests
uv run --project apps/api --frozen ruff check apps/api/src apps/api/tests apps/api/migrations
uv run --project apps/api --frozen ruff format --check apps/api/src apps/api/tests apps/api/migrations
pnpm contracts:check
pnpm typecheck:web
pnpm test:web
pnpm build:web
```

生成契约用 `pnpm contracts:generate`，禁止手改三份生成文件。运行 API、建测试账号及附件 worker 见 README；API 默认 8000，Web 5173。测试均用临时 DB；实际页面测试显式设置隔离 HERMES_DATABASE_URL，API/worker 使用相同数据库和附件根目录。首次安装联网，原机器代理 127.0.0.1:12450 仅在原机器有效。

## 不可假设与资料读取顺序

先 AGENTS + 本文件；当前任务再读 24；需求按需查 06/原始需求，架构按需查 08，整体缺口查 10。历史 TRANSFER/ZIP 和根 HANDOFF 旧段落不是最新状态。

Docker/PostgreSQL/S3、物理跨设备、生产备份恢复、真实模型及公开部署尚未验收。内存草稿可同账号重登录恢复，但不保证整页刷新/浏览器重启恢复。本机 API 在迁移时已停止，前端/worker 句柄可能存活；先检查端口，不结束未知进程。跨系统应从源码新建环境及合成数据，不复制 .local/数据库/凭据/实际.env/私有附件。

维护规则：每次交接更新本文件的当前 commit、工作树、实际测试结果及首任务。接手 agent 无需继承聊天、工具句柄或前任记忆；以源码、测试和文档为依据。
