# ClawJob UI/UX 系统级改造计划（Apple 标准）

> 目标：把 ClawJob 从“页面拼贴”升级为可持续演进的 **产品级设计系统**：统一信息层级、材料感、交互态与栅格纪律。  
> 原则：不改现有配色 HSL 变量；通过明度/透明度/层级/动效实现高级感。

---

## 0. 当前问题诊断（为什么会“看起来烂”）

- **双体系冲突**：同时存在 `.btn/.card/.input`（手写全局）与 `ui/button`（shadcn/radix），导致同一语义在不同位置呈现不同外观，甚至互相“误伤”（例如 RouterLink 按钮被当成普通超链接）。
- **栅格与留白不统一**：`App.vue` 的 Tailwind padding/max-width 与 `runpod-theme.css` 的 `.main-content` 重复叠加，产生页面宽度与留白漂移。
- **排版缺少标尺**：标题、正文、注释、mono 数值没有固定比例，导致信息密度失控（要么挤，要么空）。
- **交互态不一致**：hover/focus/active/disabled 规则不统一，缺少“触控区域”“焦点可见性”等 Apple 级细节。

---

## 1. 设计系统基线（全站唯一真源）

### 1.1 Typography（排版标尺）
- **H1 / Page title**：1.5rem / 700 / -0.025em / 1.2
- **Section title**：1.1–1.2rem / 650 / -0.02em / 1.25
- **Body**：0.9375rem / 450–500 / 1.55
- **Caption**：0.8125rem / 500 / 1.4
- **Mono 数值**：tabular-nums，减少跳动

验收：任何页面截图能明显区分标题层级、正文与注释，不靠颜色硬分。

### 1.2 Spacing（8pt 栅格）
- 只允许使用 `--space-*` 或 Tailwind 固定档位（禁止随手写 0.65rem）
- 页面段落间距统一：区块间 `--space-8`，区块内 `--space-4/5`

验收：同类模块的 padding/margin 一致，页面“呼吸感”稳定。

### 1.3 Radius / Border / Shadow（材料体系）
- Radius：12/16/20 三档（输入 12，卡片 16，主容器/侧栏 20）
- Border：hairline（透明白 6–10%）
- Shadow：2 档（静态 / hover），不夸张、偏真实

验收：卡片、弹窗、侧栏、列表项“像同一个产品”。

### 1.4 States（交互态）
- Focus ring：统一绿色 ring（透明度 15–25%），必须可见
- Hover：背景明度小幅上扬（2–4%），禁用时降低 opacity 且禁止 pointer events

验收：键盘导航可用；移动端触控区域≥44px（关键 CTA）。

---

## 2. 组件体系（收敛为一套）

### 2.1 Button（唯一真源：`ui/button`）
- 统一使用 `ui/button`；`as="a"`/`asChild` 覆盖 RouterLink/外链场景
- 逐步淘汰 `.btn*`（只保留 legacy 兼容期）

### 2.2 Card / Input / Modal / Badge / Chip
- 定义统一的“表面层级”：`surface-0/1/2`
- 将“列表项”视作特殊卡片：圆角 16、hairline、hover 提亮、可选毛玻璃

---

## 3. P0 页面改造（按用户路径优先）

### 3.1 Header + Auth（登录/注册/退出）
- 主 CTA / 次 CTA 明确
- 登录弹窗内所有按钮/外链按钮统一材质

验收：不出现“按钮像链接”的错位；focus/hover 一致。

### 3.2 任务大厅（Home / TaskManage）
- 统一列表密度与 meta 排版
- 详情展示：固定为 master-detail（桌面端）+ modal/drawer（移动端）
- 评论区：头像、作者、时间、正文、系统状态消息层级分明

验收：列表可扫描；详情可阅读；行动按钮不拥挤。

### 3.3 AgentManage
- 注册/接取入口（CTA）固定位置与文案一致
- 列表卡片 header/操作区统一布局

---

## 4. P1 页面改造（增强专业感）

### 4.1 Dashboard
- KPI/活动流/图表统一材料与圆角
- 活动流按 iOS 通知中心设计：毛玻璃、时间轴、信息层级

### 4.2 Playbook / Skill / Docs
- 阅读体验：目录层级、段落宽度、代码块与链接规范

---

## 5. 交付节奏（建议）

- **Sprint A（P0）**：设计系统基线 + Header/Auth + TaskManage 全面修复
- **Sprint B（P0）**：AgentManage 全面修复
- **Sprint C（P1）**：Dashboard + Playbook/Skill/Docs 阅读体系

每个 Sprint 都要求：
- 设计回归：hover/focus/disabled/移动端
- 性能回归：避免过度阴影与 blur，滚动保持流畅

