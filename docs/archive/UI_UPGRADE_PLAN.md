# ClawJob 视觉升级计划（待确认）

**目标：** 对标 Apple 官网的细腻感、呼吸感与精致度；**不改变现有配色（HSL 变量）**，仅通过间距、字号、阴影、圆角、毛玻璃与微交互提升档次。

**执行原则：** 优先在 `runpod-theme.css` 中完成全局/基座样式，避免在 HTML 中堆砌 Tailwind 原子类；保持响应式。

---

## Step 1：全局布局与基座（runpod-theme.css + index.css）

### 1.1 呼吸感 · 间距系统

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 新增 `--space-unit` | 无 | `8px`，作为最小栅格单位；现有 `--space-1`～`--space-10` 保持不变，在注释中标注与 unit 的关系 |
| `.main-content` 内边距 | 2rem 1rem 3rem（中屏 2rem 2rem 3rem） | 使用 `var(--space-*)`，适当增大上下留白（如 3rem 1.5rem 3.5rem / 中屏 3.5rem 2rem 4rem），增强呼吸感 |
| 区块间距 | 各处不统一 | 为 `.section-title`、`.page-section`、`.home-dashboard` 等统一使用 `--space-6` / `--space-8`，保证区块间负空间一致 |

**UI 逻辑变化：** 无；仅视觉上页面更「透气」。

---

### 1.2 字体系统 · 字重与字间距

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 标题字重级差 | 部分 600/700 | 明确层级：大标题 700～800、区块标题 600～700、小标题 600，正文 400～500 |
| 标题字间距 | 部分 -0.02em | 所有标题类（`.section-title`、`.page-title`、`.hero-block .hero-title`、`.card-header h3`、`.home-dash-feed-title`）统一 `letter-spacing: -0.025em`（略紧，更 Apple） |
| 正文与辅助文案 | 已区分 | 保持；可选为 `.hint`、`.home-kpi-label` 等统一 `font-weight: 500` 提升可读性 |

**UI 逻辑变化：** 无；仅标题与正文对比更清晰。

---

### 1.3 Header · 毛玻璃与边框

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 定位 | `position: sticky; top: 0; z-index: 100` | 保持 sticky，确保 `z-index` 高于主内容 |
| 背景 | `rgba(24,24,27,0.74)` + `backdrop-filter: blur(14px)` | `backdrop-filter: blur(20px) saturate(1.1)`；背景改为 `rgba(24,24,27,0.72)`，更通透 |
| 边框 | `1px solid var(--border-muted)` | 保持 1px，颜色改为 `rgba(255,255,255,0.06)`，更细腻 |
| 阴影 | `var(--shadow-layer-1)` | 改为极轻：`0 1px 0 rgba(0,0,0,0.08)`，不抢眼 |

**UI 逻辑变化：** 无；仅顶栏更「浮」、更精致。

---

### 1.4 卡片 · 多层复合阴影

| 变更项 | 当前 | 计划 |
|--------|------|------|
| `.card` 阴影 | `box-shadow: var(--shadow-layer-1)`，hover 时加 `--shadow-layer-2` | 默认：两层阴影（如 0 1px 0 rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.08)）；hover 增加一层（0 8px 24px rgba(0,0,0,0.12)），整体更轻、更真实 |
| 变量 | `--shadow-layer-1` 等保留 | 新增 `--shadow-card`、`--shadow-card-hover`，在 runpod-theme 中定义复合阴影，`.card` 引用 |

**UI 逻辑变化：** 无；卡片层次感更强。

---

### 1.5 全局过渡曲线

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 统一曲线变量 | 无 | 在 `:root` 增加 `--ease-apple: cubic-bezier(0.4, 0, 0.2, 1)`；`--duration-m: 300ms` |
| 应用范围 | 各组件 transition 不统一 | `.card`、`.btn`、`.nav-link`、`.filter-chip`、`.home-task-card` 等统一为 `transition: all var(--duration-m) var(--ease-apple)`（或只 transition 需要的属性） |

**UI 逻辑变化：** 无；动效更一致、更顺滑。

---

## Step 2：首页结构升级（App.vue + runpod-theme.css）

### 2.1 KPI 四宫格 · 背景微差替代硬边框

| 变更项 | 当前 | 计划 |
|--------|------|------|
| `.home-kpi-card` 边框 | `border: 1px solid var(--border-muted)` | 去掉边框；背景改为 `rgba(255,255,255,0.03)` 与相邻区块形成微差，可选 `backdrop-filter: blur(8px)` |
| 数字视觉重量 | `.home-kpi-value` 已 1.35rem / 700 | 字号改为 `1.5rem`，字重 `800`，`letter-spacing: -0.03em`，颜色保持 `var(--primary-color)` |

**UI 逻辑变化：** 无；KPI 更柔和、数字更突出。

---

### 2.2 首页 Grid 比例 · 主内容与侧栏平衡

| 变更项 | 当前 | 计划 |
|--------|------|------|
| `.home-layout`（≥1024px） | `grid-template-columns: 1fr 280px` | 改为 `1fr 300px` 或 `minmax(0, 1fr) 300px`，侧栏略增，主内容仍为主；gap 保持或略增为 `var(--space-8)` |

**UI 逻辑变化：** 无；仅比例微调。

---

### 2.3 首页任务卡片 · Hover 缩放与阴影

| 变更项 | 当前 | 计划 |
|--------|------|------|
| `.home-task-list--grid .home-task-card` | 无单独 hover | 在 runpod-theme 或 App.vue 中：hover 时 `transform: scale(1.01)`（或 1.02），`box-shadow` 使用 `--shadow-card-hover` 或更强一层；`transition` 使用 `--ease-apple` 300ms |
| 与现有 `.task-card--hover` 关系 | 已有 `.task-card--hover:hover` 的 translateY + 阴影 | 首页卡片同时带 `task-card--hover` 时，合并为：hover 时 scale(1.01) + translateY(-2px) + 增强阴影，避免冲突 |

**UI 逻辑变化：** 无；仅交互反馈更明显。

---

## Step 3：通用组件精修（runpod-theme.css + src/components/ui/*）

### 3.1 Button

| 变更项 | 当前 | 计划 |
|--------|------|------|
| Active 压感 | `.btn:active:not(:disabled) { transform: scale(0.98) }` 已有 | 保持；CVA 生成的 Button 若未用 `.btn`，在 runpod-theme 中为 `.btn` 及与 button 相关的类补充 `active:scale(0.98)` 描述，确保全局按钮一致 |
| 内边距 | 各 size 不一 | 在 runpod-theme 的 `.btn`、`.btn-sm` 中微调 padding，使视觉更平衡（如 default 略增垂直 padding） |
| 过渡 | 已有 transition | 统一为 `var(--duration-m) var(--ease-apple)` |

**UI 逻辑变化：** 无；CVA Button 与 legacy `.btn` 并存时，以 runpod-theme 覆盖/补充为准。

---

### 3.2 Input / Textarea

| 变更项 | 当前 | 计划 |
|--------|------|------|
| Focus Ring | `box-shadow: 0 0 0 2px rgba(primary-rgb, 0.2)` | 改为 3px、透明度略降（如 0.15），或使用 `ring-offset` 思路：外扩更柔和、不刺眼 |
| 过渡 | 已有 transition | 统一为 `var(--duration-m) var(--ease-apple)` |

**UI 逻辑变化：** 无。若 Input 组件使用 Tailwind 的 `ring-2 ring-ring`，则在 runpod-theme 中覆盖 `input.input`、`.input` 的 focus 样式，保证与设计一致。

---

### 3.3 Badge / Tag

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 圆角 | `border-radius: 999px` | 保持或改为 `var(--radius-full)` |
| 字体 | 0.75rem | 保持；确保 `font-weight: 500`、`letter-spacing: 0.01em`，清晰可读 |
| 内边距 | `0.18rem 0.5rem` | 略增为 `0.25rem 0.55rem`，更易点击、视觉更稳 |

**UI 逻辑变化：** 无。

---

## Step 4：细节与动态（runpod-theme.css + App.vue）

### 4.1 统一过渡曲线

| 变更项 | 计划 |
|--------|------|
| 卡片、按钮、导航链接、筛选芯片、首页任务卡片 | 全部使用 `transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1)`（或通过变量 `--ease-apple`、`--duration-m`） |
| 仅需部分属性时 | 可写为 `transition: transform 300ms var(--ease-apple), box-shadow 300ms var(--ease-apple), border-color 300ms var(--ease-apple)` 等，避免 `all` 影响不必要的属性 |

**UI 逻辑变化：** 无。

---

### 4.2 骨架屏 .tw-skeleton

| 变更项 | 当前 | 计划 |
|--------|------|------|
| 动画 | `skeleton-shine` 1.2s ease-in-out infinite | 改为 1.5s，曲线 `cubic-bezier(0.4, 0, 0.2, 1)`，使闪动更平滑、不突兀 |
| 渐变 | 25% / 50% / 75% | 可微调为 30% / 50% / 70%，光带更柔和 |

**UI 逻辑变化：** 无。

---

## 文件修改清单（确认后执行）

| 文件 | 修改内容 |
|------|----------|
| `src/styles/runpod-theme.css` | 变量（--space-unit、--ease-apple、--duration-m、--shadow-card、--shadow-card-hover）；Header 毛玻璃与边框；.card 复合阴影；.btn / .input / .badge 精修；.nav-link、.filter-chip、.task-card--hover 过渡；.tw-skeleton 动画；.main-content 留白；.home-layout 比例 |
| `src/assets/index.css` | 可选：补充与 runpod-theme 一致的过渡变量（若希望 Tailwind 层也可用） |
| `src/App.vue` | .home-kpi-card、.home-kpi-value 样式调整（去边框、背景微差、数字字重）；.home-task-list--grid .home-task-card hover（scale + 阴影）；.home-layout gap；与 runpod-theme 中 home 相关类保持一致 |
| `src/components/ui/button/index.ts` | 在 CVA 的 base 中增加 `transition-colors` 或 `transition-all` + duration/ease（若用 Tailwind 类）；或依赖 runpod-theme 对 .btn 的覆盖 |
| `src/components/ui/input/Input.vue` | 可选：focus-visible 的 ring 类改为更柔和（如 ring-2 ring-primary/20 ring-offset-2）；或完全由 runpod-theme 的 input.input:focus 覆盖 |
| `src/components/ui/card/Card.vue` | 可选：增加 `shadow-sm` 或类名供 runpod-theme 的 .card 覆盖；当前 Card 已用 `shadow-sm`，runpod-theme 的 .card 会叠加，需确保不冲突 |

---

## 响应式

- 所有间距、字号、圆角均保持或使用现有 `@media`；新增变量不改变断点逻辑。
- 移动端：Header 与 main-content 的 padding 已在 runpod-theme 中有 768px 断点，将沿用并仅做数值微调（更大留白）。

---

## 总结

- **配色：** 不改任何 HSL / 色值。
- **逻辑：** 无功能/交互逻辑变更，仅视觉与动效。
- **优先级：** 先 runpod-theme.css 全局与基座，再 App.vue 首页，最后 UI 组件与骨架屏。

请确认以上清单与 UI 逻辑描述是否同意；确认后将按此计划逐项修改代码。
