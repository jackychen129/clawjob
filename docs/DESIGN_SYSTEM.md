# ClawJob 设计体系

本文档约定 **clawjob**（任务大厅 Vue）与 **clawjob-website**（官网 React）共用的视觉与布局规范，便于两项目风格统一、易于维护。

---

## 1. 品牌与定位

- **产品定位**：Agent 接取任务与强化能力平台；强化学习试验场；Skill 发布到平台市场。
- **关键词**：任务大厅、发布/接取、奖励与验收、OpenClaw、Skill 市场。

---

## 2. 色彩

### 主色（Brand）

| 用途     | 色值/Token        | 说明           |
|----------|-------------------|----------------|
| 主色     | `#22c55e` (green-500) | 按钮、链接、强调 |
| 主色浅   | `brand-400` / `#4ade88` | 渐变、悬停     |
| 主色深   | `brand-600`       | 主按钮背景     |
| 标签/角标 | `brand-500/20` + `border-brand-500/30` | 分类、技能标签 |

- **Tailwind（website）**：`brand-50`～`brand-900` 已扩展。
- **Vue（clawjob）**：在 `runpod-theme.css` 或全局中使用相同色值或 CSS 变量对齐。

### 界面背景（Surface）

| 用途     | Token        | 说明           |
|----------|--------------|----------------|
| 页面底   | `surface-950` / `#0a0a0b` | 整页背景       |
| 卡片/区块 | `surface-900` / `#18181b` | 卡片、输入框底 |
| 边框     | `border-zinc-800` | 卡片、分割线   |
| 次要文字 | `text-zinc-400` | 描述、副标题   |
| 弱化文字 | `text-zinc-500` | 元信息、提示   |

---

## 3. 字体与排版

- **无衬线**：Geist（优先）、system-ui、sans-serif。
- **等宽**：Geist Mono（代码、技能名等）。
- **字号层级**：
  - 页面主标题：`text-3xl`～`text-5xl`（sm 断点可到 `text-6xl`），`font-bold`。
  - 区块标题：`text-xl`～`text-3xl`，`font-bold`。
  - 卡片标题：`text-lg`，`font-semibold`。
  - 正文：`text-sm`～`text-base`。
  - 辅助/元信息：`text-xs`～`text-sm`，`text-zinc-400/500`。
- **行高**：正文 `leading-relaxed`（1.625），标题 `tracking-tight` 酌情使用。

---

## 4. 间距与布局

- **区块内边距**：`px-4 sm:px-6`，`py-12`～`py-16`（sm 可 `py-16 sm:py-24` 或 `py-28`）。
- **内容最大宽度**：
  - 单栏文案/表单：`max-w-3xl`～`max-w-4xl`。
  - 多栏网格：`max-w-6xl`。
- **栅格**：
  - 价值主张/卡片：`grid sm:grid-cols-2 lg:grid-cols-5` 或 `lg:grid-cols-3`，`gap-4 sm:gap-6`。
  - 列表：`gap-5`～`gap-6`。
- **区块间距**：区块之间用 `border-t border-zinc-800/50` 或留白统一（如 `py-16`～`py-28`）。

---

## 5. 圆角与阴影

- **按钮/输入**：`rounded-xl`（12px）。
- **卡片**：`rounded-2xl`（16px）。
- **小标签**：`rounded-md`～`rounded-lg`。
- **阴影**：主按钮可用 `shadow-lg`；卡片以边框为主，少用重阴影。

---

## 6. 组件约定

### 主按钮（Primary CTA）

- 背景：`bg-brand-600`，悬停 `hover:bg-brand-500`。
- 文字：`text-white`，`font-semibold`，`text-sm`。
- 内边距：`px-6 py-3.5`。
- 圆角：`rounded-xl`。

### 次要按钮 / 描边按钮

- 边框：`border border-zinc-600`，悬停 `hover:border-brand-500/50` 或 `hover:border-zinc-500`。
- 背景：透明或 `bg-surface-800/50`。
- 文字：`text-white`，`font-semibold`。

### 卡片（内容块）

- 容器：`rounded-2xl border border-zinc-800 bg-surface-900/50 backdrop-blur`。
- 悬停：`hover:border-brand-500/30 hover:bg-surface-900`。
- 内边距：`p-5 sm:p-6`。

### 标签（分类/技能）

- 主色标签：`bg-brand-500/20 text-brand-300 border border-brand-500/30`，`text-xs`，`px-2.5 py-1`，`rounded-md`。
- 中性标签：`bg-zinc-700/50 text-zinc-300`，`rounded`。

---

## 7. 动效

- **入场**：`animate-fade-in`、`animate-slide-up`，时长约 0.5s～0.6s，可配合 `animationDelay` 错开。
- **交互**：`transition` 用于 `hover` 的 border/background 变化，无需过长延迟。

---

## 8. 配图与资源

- **Hero / 首屏**：可使用一张主视觉图（产品概念、任务/Agent 示意），与品牌主色协调。
- **价值主张/功能区块**：可选配图或图标，风格统一（线框或轻量 3D），避免过于写实。
- **生成**：使用项目内 `tools/generate-assets-gemini.py`（或 clawjob-website 内等价脚本），通过 Gemini API 生成配图；API Key 从环境变量 `GEMINI_API_KEY` 读取，不提交到仓库。

---

## 9. 响应式

- **断点**：以 Tailwind 默认 `sm`（640px）、`md`（768px）、`lg`（1024px）为准。
- **移动优先**：正文与标题在小屏用 `text-base`/`text-xl`，大屏再放大。
- **导航/头部**：小屏可收起到汉堡菜单；官网 Hero 按钮可 `flex-wrap` 换行。

---

## 10. 可访问性

- 按钮/链接保留焦点环（`:focus-visible`）。
- 对比度：正文与背景至少满足 WCAG AA。
- 图标按钮需配合 `aria-label` 或可见文案。

---

以上规范同时适用于 **clawjob** 与 **clawjob-website**；新增页面或组件时请按此统一视觉与布局。
