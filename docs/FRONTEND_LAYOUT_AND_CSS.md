# ClawJob 前端页面布局与 CSS 构建说明

本文档供 AI（如 Gemini）或开发者根据结构和约定进行**针对性修改**：改哪一页、改哪一层、样式应写在哪个文件、如何构建与预览。

---

## 一、技术栈与构建

| 项目 | 说明 |
|------|------|
| 框架 | Vue 3 + TypeScript |
| 路由 | Vue Router，**Hash 模式**（`createWebHashHistory`），路径如 `/#/tasks`、`/#/agents` |
| 构建工具 | **Vite 5**（`vite.config.ts`） |
| 样式 | **Tailwind CSS 3** + 全局 CSS 变量 + 少量手写全局/组件 scoped |
| 入口 | `index.html` → `<script type="module" src="/src/main.ts">` → `main.ts` 挂载 `App.vue` |

### 常用命令

```bash
cd frontend
npm install
npm run dev      # 开发：http://localhost:3000
npm run build    # 生产构建，输出到 frontend/dist
npm run preview  # 本地预览构建结果
```

### 样式构建链路

1. **Vite** 处理入口与 Vue 单文件（SFC）。
2. **PostCSS**（在 `vite.config.ts` 的 `css.postcss.plugins` 中）依次执行：
   - **tailwind**：扫描 `tailwind.config.js` 的 `content`（`./index.html`、`./src/**/*.{vue,js,ts,jsx,tsx}`），生成工具类并应用 `theme.extend`。
   - **autoprefixer**：补前缀。
3. **全局样式加载顺序**（在 `main.ts` 中）：
   - `import './assets/index.css'` — Tailwind 三层（base/components/utilities）+ `:root` CSS 变量（HSL 形式，供 Tailwind theme 使用）。
   - `import './styles/runpod-theme.css'` — 主题变量、全局布局、Header/主内容区、首页、卡片/按钮等。

因此：**修改全局布局、主题色、Header、主内容区、首页结构**应优先改 `runpod-theme.css` 或 `App.vue` 内样式；**仅某页或某组件**用该页/组件的 `<style scoped>` 或 Tailwind 工具类。

---

## 二、目录结构（与布局/样式相关的部分）

```
frontend/
├── index.html                 # 单页入口，<div id="app">，首屏 Loading 占位
├── vite.config.ts             # Vite + PostCSS (Tailwind + autoprefixer)
├── tailwind.config.js         # Tailwind content、theme.extend（颜色/圆角用 CSS 变量）
├── package.json               # scripts: dev, build, preview
├── src/
│   ├── main.ts                # 挂载 App、router、pinia、i18n；引入 assets/index.css、styles/runpod-theme.css
│   ├── App.vue                # 根组件：全局壳（Header + 主内容区）+ 首页内容或按路由渲染子视图
│   ├── router/index.ts        # 路由表：path → component 映射
│   ├── assets/
│   │   └── index.css          # @tailwind base/components/utilities + :root 变量（HSL）
│   ├── styles/
│   │   └── runpod-theme.css   # 主题变量、.app-container、.app-header、.main-content、.home-*、.section-*、.card、.btn 等
│   ├── views/                 # 页面级组件，按路由渲染在 <main class="main-content"> 内
│   │   ├── DashboardView.vue
│   │   ├── LeaderboardView.vue
│   │   ├── PlaybookView.vue
│   │   ├── TaskManageView.vue
│   │   ├── AgentManageView.vue
│   │   ├── AccountPage.vue
│   │   ├── SkillPage.vue
│   │   ├── AdminView.vue
│   │   ├── DocsPage.vue
│   │   ├── ManualPage.vue
│   │   ├── OpenClawQuickstartPage.vue
│   │   └── ...
│   ├── components/            # 可复用组件
│   │   ├── ui/                # 通用 UI：Button, Input, Card, Textarea 等（含 Tailwind + 少量 scoped）
│   │   │   ├── button/
│   │   │   ├── input/
│   │   │   ├── card/
│   │   │   └── textarea/
│   │   ├── TaskCard.vue
│   │   ├── AgentCard.vue
│   │   └── ...
│   ├── locales/               # 中英文文案 zh-CN.ts、en.ts
│   ├── stores/                # Pinia（如 auth）
│   ├── api.ts                 # 接口封装
│   └── lib/utils.ts           # 如 cn() 合并 Tailwind 类名
```

---

## 三、整体页面布局（App.vue）

### 3.1 结构概览

- **始终存在**：
  - 根节点：`<div id="app" class="app-container relative min-h-screen">`
  - 背景装饰：`.aura-glow`（两处）
  - **顶栏**：`<header class="app-header ...">` 内：品牌区、`<nav class="header-nav">`（首页、实况、排行榜、任务管理、Agent 管理、Playbook、Skill、管理后台）、`<div class="header-actions">`（语言、用户名、信用点、账户、登出/登录）
- **按条件显示**：
  - 顶部横幅：OAuth 错误、游客提示、发布后引导注册、草稿提示等（`.oauth-error-banner`、`.guest-hint-banner` 等）
- **主内容**：`<main class="main-content relative z-0 px-6 sm:px-8 md:px-12 max-w-7xl mx-auto w-full flex-1 py-8 md:py-12" :key="route.path">`
  - 内部由 **路由 path** 决定：要么渲染**整页视图**（如 `SkillPage`、`DashboardView`、`TaskManageView`、`AgentManageView` 等），要么渲染**首页**（`route.path === '/'` 时的 `home-wrap`：KPI、开放任务列表、侧栏实时动态、我创建的任务等）。

### 3.2 路由与渲染对应（router + App.vue）

| 路径 | 渲染内容 | 说明 |
|------|----------|------|
| `/` | 首页 | 在 App.vue 内联：KPI 卡片、开放任务、右侧实时动态、用户创建的任务 |
| `/dashboard` | DashboardView | 实况页 |
| `/leaderboard` | LeaderboardView | 排行榜 |
| `/playbook` | PlaybookView | 入门与租赁 + Agent 模板市场 |
| `/rental` | 重定向到 `/playbook` | — |
| `/tasks` | TaskManageView | 任务管理 |
| `/agents` | AgentManageView | Agent 管理 |
| `/skill` | SkillPage | Skill 安装与说明 |
| `/account` | AccountPage | 账户与信用点 |
| `/admin` | AdminView | 管理后台（需管理员） |
| `/docs`、`/docs/manual` 等 | DocsPage / ManualPage / OpenClawQuickstartPage | 文档类 |

首页是**唯一**不通过 `router` 渲染独立 view 的页面：在 App.vue 里用 `v-else`（即 `route.path === '/'`）渲染 `home-wrap` 及内部区块。

### 3.3 首页（`/`）内部结构（便于改版）

- `.home-wrap.apple-layout`
  - `.home-dashboard`：KPI 四宫格（`.home-kpi`、`.home-kpi-card`）
  - `#task-list.section-title`：「可接取任务」标题
  - `.home-layout`（Grid）：
    - **左** `.home-main`：搜索/筛选/排序（`.home-toolbar`）、任务列表（`.home-task-list--grid`）、加载更多
    - **右** `.home-sidebar`：发布任务按钮（`.home-publish-btn`）、实时动态卡片（`.home-sidebar-feed`，最多 10 条）
  - 登录后：`.home-my-created`（我当前创建的任务）

修改首页时：**左侧**改 App.vue 里 `home-main` 下的模板与数据；**右侧**改 `home-sidebar`；**样式**优先在 `App.vue` 底部 `<style>` 或 `runpod-theme.css` 中查找 `.home-*`、`.section-*` 等类。

---

## 四、CSS 文件职责与修改指南

### 4.1 `src/assets/index.css`

- 内容：`@tailwind base;` / `@tailwind components;` / `@tailwind utilities;`，以及 `@layer base { :root { ... } }`。
- `:root` 定义的是 **HSL 无括号值**（如 `--background: 240 5% 4%;`），供 `tailwind.config.js` 的 `theme.extend.colors` 使用（如 `background: 'hsl(var(--background))'`）。
- **何时改**：需要改 Tailwind 使用的语义色（background、foreground、primary、border、muted 等）或全局 base 层时改这里；**不要**在这里写具体页面布局或组件样式。

### 4.2 `src/styles/runpod-theme.css`

- 主题变量（`:root`）：如 `--primary-color`、`--text-primary`、`--card-background`、`--border-color`、`--radius-sm`、`--space-*`、`--font-*` 等，以及阴影、留白。
- 全局布局：`.app-container`、`.app-header`、`.header-content`、`.header-brand`、`.header-nav`、`.nav-link`、`.header-actions`、`.main-content`。
- 首页相关：`.home-wrap`、`.home-layout`、`.home-main`、`.home-sidebar`、`.home-toolbar`、`.home-*` 系列（含侧栏、筛选、任务列表栅格等）。
- 通用组件样式：`.card`、`.card-content`、`.btn`、`.btn-primary`、`.btn-secondary`、`.input`、`.section-title`、`.section-full`、表格、空状态、骨架屏（`.tw-skeleton`）等。
- **何时改**：改 Header、主内容区宽度/留白、首页整体布局、卡片/按钮/输入框的全局样式、主题色或间距变量时，优先改本文件。

### 4.3 `App.vue` 内 `<style>`

- 与首页或全局壳强相关的补充样式：如 `.section-head`、`.home-dashboard`、`.home-kpi-*`、`.home-dash-feed`、`.home-sidebar-feed`、`.home-activity-*`、`.home-task-list--*`、`.home-task-card` 等；以及部分 modal、表单的布局。
- **何时改**：改首页 KPI、首页侧栏动态、首页任务卡片在首页中的表现、或仅首页用到的区块时，在 App.vue 的 style 里增删或修改类。

### 4.4 各页面视图（`src/views/*.vue`）

- 每个 view 通常自带 `<style scoped>`，类名多带页面前缀（如 `AgentManageView` 的 `.agent-manage-view`、`.agent-block`、`.one-click-hint-card`）。
- **何时改**：只改某一页的布局或样式时，只改对应 view 的 template 与 `<style scoped>`，避免动全局或首页。

### 4.5 通用 UI 组件（`src/components/ui/*`）

- 使用 Tailwind + `lib/utils.ts` 的 `cn()` 做类名合并，部分带少量 scoped 样式。
- **何时改**：改按钮、输入框、卡片等通用组件的外观或变体时，改对应组件；若需全局一致，再配合 `runpod-theme.css` 中的 `.btn`、`.card` 等。

### 4.6 Tailwind 工具类（内联）

- 大量使用在模板中，如 `class="flex gap-2 items-center"`、`class="text-zinc-500 text-sm"`、`class="rounded-md border border-input bg-background"` 等。
- **何时改**：小范围调整间距、字号、颜色、flex/grid 时，直接改该元素的 class；若多处一致，可考虑在 theme 或 runpod-theme 中增加语义类或变量。

---

## 五、命名与布局约定（便于 AI 定位）

- **布局块**：`app-container`、`app-header`、`main-content`、`home-wrap`、`home-layout`、`home-main`、`home-sidebar`。
- **首页**：`home-dashboard`、`home-kpi`、`home-task-list`、`home-sidebar-feed`、`home-my-created`。
- **通用区块**：`section-title`、`section-head`、`section-full`、`card`、`card-content`、`card-header`。
- **任务相关**：`task-card`、`task-card__title`、`task-card__meta`、`task-actions` 等（BEM 风格）。
- **状态与骨架**：`tw-skeleton`、`tw-empty-state`、`loading`、`hint`、`error-msg`。
- **修改时**：先根据“要改的是整站 / 顶栏 / 首页 / 某页”选文件（runpod-theme / App.vue / 某 view），再按类名搜索（如 `home-sidebar`、`section-title`）做针对性修改。

---

## 六、Tailwind 配置要点（tailwind.config.js）

- **content**：`./index.html`、`./src/**/*.{vue,js,ts,jsx,tsx}`，只有这些里的类会被生成。
- **darkMode**：`'class'`（如需暗色可给根节点加 `class="dark"`）。
- **theme.extend**：颜色、圆角等引用 CSS 变量（如 `hsl(var(--primary))`、`var(--radius)`），与 `index.css` 的 `:root` 和 `runpod-theme.css` 的变量一致即可扩展。
- **plugins**：`tailwindcss-animate`。

修改主题色或圆角时，可同时改 `index.css` 的 `:root`、`runpod-theme.css` 的 `:root`、以及 `tailwind.config.js` 的 `theme.extend`，保持变量名一致。

---

## 七、总结：按需求选改哪里

| 需求 | 建议修改位置 |
|------|----------------|
| 顶栏、导航、主内容区宽度/留白 | `runpod-theme.css` |
| 首页 KPI、首页左右栏、首页任务列表/侧栏 | `App.vue`（template + style） + 必要时 `runpod-theme.css` 的 `.home-*` |
| 主题色、全局间距/圆角变量 | `index.css` 的 `:root` + `runpod-theme.css` 的 `:root` |
| 某独立页（任务管理、Agent 管理、Playbook 等） | 对应 `src/views/xxx.vue` 的 template + `<style scoped>` |
| 按钮/输入框/卡片等通用组件 | `src/components/ui/*` + 必要时 `runpod-theme.css` 的 `.btn`、`.card` |
| 新增页面 | `router/index.ts` 加路由，`App.vue` 的 `<main>` 里加 `v-else-if="route.path === '/新路径'"` 渲染新 view，新 view 用 scoped 样式 |

按上述结构即可在**不破坏现有布局**的前提下，对 ClawJob 前端做针对性修改；构建与预览使用 `npm run dev` / `npm run build` / `npm run preview`。
