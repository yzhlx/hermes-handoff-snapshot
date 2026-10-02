# DESIGN.md — Hermes Learning OS 视觉语言规格

> 本文件把参考图的视觉语言写成**可执行数值**，是 t14 重做页面的验收依据。
> 唯一实现来源是 `apps/web/src/shared/ui/tokens.css`；页面与组件只引用令牌，不写死颜色与尺寸。
>
> **数据来源与测量方法**：参考图为 `ui参考图/Hermes首页.png`（1448×1086 整窗截图，≈1440 CSS 宽，误差 ≤1%），
> 用 Pillow 逐像素游程/色块测量（脚本与原始 JSON：`.foreman/results/visual-parity-current-measure.json`）；
> 当前实现为 1440×900 视口下的构建产物，用 CDP `getBoundingClientRect` + `getComputedStyle` 实测。
> 两者并排比对图：`.foreman/results/visual-parity-baseline.png`，逐条差异：`.foreman/results/visual-parity-baseline.json`。
> 标注「估算」的条目是目测，其余均为像素/DOM 实测。

---

## 1. 令牌清单（`tokens.css`，唯一来源）

| 分组 | 令牌 | 值 | 用途 |
| --- | --- | --- | --- |
| 表面 | `--surface-pure` / `--surface-card` / `--surface-app` / `--surface-canvas` | `#FFFFFF` / `#FDFDFD` / `#FBFBF9` / `#F3F2EF` | 卡片 / 应用表层 / 画布 |
| 表面 | `--surface-beige` / `--surface-muted` / `--surface-raised` | `#F4F0E7` / `#EEE8DE` / `#F8F5EF` | 暖米色带 / 静音块 / 抬升块 |
| 表面 | `--surface-green-tint` / `--surface-green-tint-strong` | `#E5F1E2` / `#D8EAD6` | 选中态、浅绿强调底 |
| 文本 | `--text-primary` / `--text-secondary` / `--text-tertiary` / `--text-inverse` | `#24241F` / `#706D65` / `#857F73` / `#F8F5EE` | 正文 / 次级 / 装饰 / 反白 |
| 边框 | `--border-default` / `--border-subtle` / `--border-strong` | `#E6E1D8` / `rgba(68,61,50,.10)` / `#D8D2C6` | 卡片描边 / 分隔线 / 强描边 |
| 强调 | `--accent-primary` / `--accent-primary-hover` | `#317B43` / `#2A6F3B` | 实心绿主操作 |
| 强调 | `--accent-sage/lime/warm/clay/indigo/plum/ink` + `-soft`/`-ink` | 见 §3 | 数据驱动卡片的徽章色 |
| 状态 | `--status-success` / `--status-warning` / `--status-danger` | `#7F9676` / `#BE9B5D` / `#AD756B` | 状态点、提示 |
| 字体 | `--font-sans` / `--font-serif` | 系统字体栈 / Georgia | 全局 / 品牌字标 |
| 字号 | `--text-xs…--text-title` | 11 / 12 / 14 / 15 / 17 / 19 / 22 / 26 / `clamp(28px,3vw,40px)` | 阶梯 |
| 行高 | `--leading-tight/snug/normal/relaxed` | 1.4 / 1.5 / 1.6 / 1.8 | 标题 / 短文本 / 正文 / 长文 |
| 字重 | `--weight-medium` / `--weight-semibold` | 500 / 550 | 标题 / 强调标题 |
| 间距 | `--space-1…--space-12` | 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 56 / 64 / 72 | 8px 基准 |
| 圆角 | `--radius-xs/sm/md/lg/xl/pill` | 6 / 10 / 14 / 20 / 26 / 999 | 控件 / 卡片 / 药丸 |
| 阴影 | `--shadow-soft/card/raised/dialog` | 见 tokens.css | 极轻层次 |
| 动效 | `--motion-fast/normal` + `--ease-standard/out` | 160 / 220ms，`ease` / `cubic-bezier(.2,.7,.3,1)` | 过渡 |
| 控件 | `--control-height` / `--control-height-compact` | 44 / 40 | 触达尺寸 |
| 布局 | `--layout-sidebar-width` / `--layout-topbar-height` / `--layout-gutter` / `--layout-content-max` | 240（≤1024 200） / 88（≤1024 122，≤600 不声明） / 48 / 1160 | 外壳 |
| 层级 | `--z-topbar/sticky/overlay/dialog/toast` | 30 / 40 / 60 / 70 / 80 | 叠放 |

兼容别名（`--canvas` `--panel` `--card` `--ink` `--muted` `--border` `--sage` `--radius`）只服务于尚未迁移的页面样式，新代码一律用语义令牌。

---

## 2. 参考图实测：布局与密度（每条标注来源元素）

| 规格 | 参考图实测 | 当前实现 | 来源（参考图元素） |
| --- | --- | --- | --- |
| 内容列宽 | ≈1165px（x 230→1395） | `app-main` 从 x240 起、`home-page` 再内缩到 x304（宽 1057） | 首页整体内容区边界 |
| 学科卡尺寸 | **184×129**，列间距 **11.6**，6 列（行宽 1166） | 462×44 的文字行，按分组两块面板 | 「我的学科」六张卡（x232..1398 / y408..536） |
| 学科卡内边距 | 顶 13 / 左 17 / 底 19（徽章 45，标题 16px，副标题 12px） | 8px 0（行式） | 同上，卡片内徽章与文字行 |
| 学科卡圆角 | ≈12（估算，目测） | 14（`.subject-entry`）/ 10（行） | 同上 |
| 徽章 | **45×45**，圆角 ≈12，图标约 22px | 28×28，圆角 8，图标 16px | 六张卡左上徽章（x249..294 / y421..465） |
| 学科标题 / 副标题 | 16px（字形高 16）/ 12px（字形高 11） | 15px / 无副标题 | 卡片文字行 y477..492 / y507..517 |
| 区块标题 | 19px（字形高 19，字重约 500–600） | 19px / 行高 28.5 / 字重 500 ✅ 已一致 | 「我的学科」y372..390、「继续上次」y570..588 |
| hero | **207px** 高、满内容宽；三层米色带 `#F3EEE6 → #EFEBE2 → #EAE6DA`（右侧为实景照片）。**207 是下限**：本实现取 284px，因为参考图该区域是照片，我们的 hero 还要承载 30px 金句 + 署名 + 收藏/不喜欢两个动作 | 249px 高、1057px 宽、单一平色 `#F4F0E7` | 首页顶部米色带（x700 纵向游程 y139..345） |
| hero 内文字 | 日期 12–13px / 金句 28–30px / 作者 14px | 金句 17px、作者 12px | 同上（金句两行 y198..226、y243..270） |
| 区块节奏 | hero→标题 **27**、标题→卡片 **18**、卡片→下一块 **17** | hero 内边距 40、区块间距 26 | 首页相邻区块的边界实测 |
| 首屏预算（900px） | hero + 我的学科 + 继续上次 + 可考虑继续 + 学习方法 + 最近变化（整窗 1086px 内） | 仅 hero + 学科（「继续学习」从 y937 开始） | 首页整窗截图内容分布 |
| 主操作绿 | `#317B43`（实心按钮） | `--accent-primary` = `#317B43` ✅ | 「继续学习」「进入学习」按钮 |
| 选中态 | 浅绿底 `#E5F1E2` + 绿字 | 侧栏选中项同值 ✅ | 侧栏「书房」选中行 |

**密度目标（t14 验收）**：1440×900 内至少容纳 hero + 学科卡 + 继续上次；900px 之内不出现「只有 hero 和学科」。

---

## 3. 色板使用规则（强调色）

参考图「我的学科」六张卡的徽章底色与图标色（soft 为底、ink 为图标线条），与令牌一一对应：

| 参考图学科 | 参考图 soft / ink（实测） | 令牌 | 令牌值 soft / ink | 对比度 |
| --- | --- | --- | --- | --- |
| 高等数学（Σ） | `#D1E6D0` / `#003B0B` | `--accent-sage-*` | `#D5E8D2` / `#14532A` | 7.09:1 |
| 信号与系统（波形） | `#D4E5F6` / `#12467A` | `--accent-indigo-*` | `#D8E6F7` / `#1C4A7C` | 7.15:1 |
| 电路基础（芯片） | `#FEE4BB` / `#824500` | `--accent-warm-*` | `#FDE4B8` / `#7A4708` | 6.21:1 |
| 英语（A） | `#E3D8FA` / `#3E3079` | `--accent-plum-*` | `#E5DCFA` / `#43327C` | 8.03:1 |
| 政治（柱式建筑） | `#F9C9C7` / `#8D0000` | `--accent-clay-*` | `#F8CFC9` / `#8A2B22` | 6.03:1 |
| 自由学习（四格） | `#DDE2E8` / `#364352` | `--accent-ink-*` | `#DFE4EA` / `#3A4754` | 7.43:1 |
| （参考图未出现） | — | `--accent-lime-*` | `#E9F0C9` / `#4F5C22` | 6.16:1 |

**使用规则**

1. 每个学科/方法**一个稳定颜色**：同一学科在首页 / 学科空间 / 学习记录 / 复盘颜色与图标完全一致（由 `subject-meta.ts` 的语义表 + id 稳定散列保证）；同一分组内不同学科颜色必须不同。
2. 辅助色（上表七组）**只出现在徽章与极小状态点**，面积受控；正文、边框、大面积底色一律不用辅助色。
3. 实心绿 `--accent-primary` 是**主操作色**：同一屏内不超过 1 个实心绿按钮；次操作使用软绿底 + 绿字（`.secondary`），其余使用文字按钮。
4. 徽章 = 该学科强调色 soft 底 + 同色 ink 图标；不得用 ink 作大面积底色，也不得用 soft 作文字色。
5. 禁止：霓虹紫、赛博朋克、整屏黑底、大蓝紫渐变、重阴影、彩虹图标墙（AGENTS.md §7.3）。
6. 对比度下限（实测已满足）：ink 对 soft ≥ 6:1；正文 `#24241F` 对 `#FDFDFD` ≥ 15:1；次级文本 ≥ 5:1；绿底白字 ≥ 5:1。

---

## 4. 学科外观规则（t13 根因修复）

`apps/web/src/features/knowledge/subject-meta.ts`：

1. **强调色与图标按学科身份取**，分组（`group_label`）只决定分组标题与排序，不再决定颜色。
2. 语义层（关键词 → 图标 + 强调色）对应参考图六个学科：电路→`circuit`/warm、信号→`signal`/indigo、线性代数→`matrix`/lime、数学→`sigma`/sage、英语→`language`/plum、政治→`politics`/clay、自由学习→`grid`/ink。
3. 兜底层：未命中语义表时按学科 id 稳定散列（7 色 × 8 图标池），新增学科零改动、外观可复现。
4. `/records` 只给 `subject_id` + `subject_name`，因此 `recordSubjectMeta` 同时把名字传给 `subjectMeta`，否则同一学科在记录页会换色。

---

## 5. hero 令牌化配方（参考图 hero 是照片，素材不可得）

必须做出体积与层次，**不能是一块纯平米色**。实现方式（t14 应用）：

| 层 | 规格 | 目的 |
| --- | --- | --- |
| 底色 | `--bg-hero`（`#F4F0E7`） | 暖米色底 |
| 纵向色带 | 顶部 `#F3EEE6` → 中部 `#EFEBE2` → 底部 `#EAE6DA`（参考图 x700 实测三层） | 模拟照片的明暗体积 |
| 极淡纹理 | 45° 细纹 `rgba(140,118,99,.035)`，间距 6px（估算） | 避免大面积平色发“空” |
| 边缘内描边 | `inset 0 0 0 1px rgba(68,61,50,.06)` + `--radius-lg` | 让色带边界收口 |
| 高度 | ≥207px（参考图实测）。**下限而非硬指标**：本实现 284px——hero 里还有 30px 金句 + 署名 + 两个动作，压到 207 只能靠收内边距或缩字号，属于把内容挤坏换数字对齐，不做 | 与参考图体量一致 |
| 右侧母题 | ≥1025px 显示（≤1024 隐藏，宽度让给 30px 金句）；体量 = hero 宽的 ≈39%，`--accent-warm-ink` + `stroke-width: 2`（1440 下渲染 ≈3.07px），实测描边/底色对比度 **5.4:1** | 参考图该处是照片，视觉重量必须相当 |
| 文字层级 | 日期 12–13px / 主句 28–30px / 署名 14px | 参考图 hero 内排版 |

建议令牌（已定义在 `tokens.css`，t14 直接引用）：`--bg-hero-top` `--bg-hero-mid` `--bg-hero-bottom` `--hero-texture` `--hero-inner-border` `--layout-hero-height`（207px）。

---

## 6. 与参考图的差距清单（t14 的输入）

完整逐条差异（当前值 / 参考值 / 拟修值）见 `.foreman/results/visual-parity-baseline.json`，摘要：

1. 学科入口形态：44px 文字行 → **184×129 彩色卡片**，6 列网格，徽章 45×45 置顶。
2. 学科卡文案：只有学科名 → 名称 + 一行 12px 次要说明。
3. hero：纯平米色 249px → **207px 满宽分层色带**（§5）。
4. 密度：首屏只有 hero + 学科 → **首屏 hero + 学科卡 + 继续上次**。
5. 内容列：页面再内缩 64px → 占满内容列（留白 24–32px）。
6. 区块间距：26px → 16–20px；卡片内边距 24–28px → 16–20px。
7. 主操作：同屏 ≤1 个实心绿（当前首页「开始一段学习」仍是软绿，符合次操作定位，保持）。

---

## 7. 边界与约束

- 无网络字体、无新增依赖、无路由库；图标一律 `aria-hidden`，按钮可访问名称只由文字构成。
- 动效 160–220ms，`prefers-reduced-motion` 下全部关闭（已有全局规则）。
- 令牌只加不改语义：新增颜色须先进 `tokens.css` 并在此登记来源与对比度。
- 本文件只描述**视觉语言**；页面结构与数据形态由各页面组件与 `features/*` 渲染层决定。
