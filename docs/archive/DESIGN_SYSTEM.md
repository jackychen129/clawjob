# ClawJob 设计体系（归档索引）

> **⚠️ 本文档已 supersede — 完整规划请参阅主文档：**
>
> **[DESIGN_OVERHAUL_MASTER_PLAN.md](../DESIGN_OVERHAUL_MASTER_PLAN.md)**  
> （Design & UX 主规划 · 2026-05-31）

---

## 快速链接

| 文档 | 说明 |
|------|------|
| [DESIGN_OVERHAUL_MASTER_PLAN.md](../DESIGN_OVERHAUL_MASTER_PLAN.md) | **主规划**：愿景、原则、视觉 v2、动效、IA、线框、分阶段 rollout |
| [UI_UX_REDESIGN_PLAN.md](UI_UX_REDESIGN_PLAN.md) | Apple 标准组件收敛与 P0 页面改造（历史） |
| [FRONTEND_LAYOUT_AND_CSS.md](FRONTEND_LAYOUT_AND_CSS.md) | 布局与 CSS 实现说明（历史） |
| [clawjob-website/DESIGN_TODO.md](../../clawjob-website/DESIGN_TODO.md) | 官网 Phase 4 checklist |

---

## 仍有效的基线摘要（实施 Phase 1 前沿用）

以下为 **v1 设计体系** 核心约定，Phase 1 Token 化时迁移至 `design-tokens.json`，细节以主规划 §3 为准。

### 品牌色

- 主色：`#22c55e`（green-500）
- 页面底：`#0a0a0b` · 卡片：`#18181b` / `#27272a`
- 边框：hairline `rgba(255,255,255,0.06)`

### 字体（v1 → v2 升级见主规划）

- v1：Inter + system-ui
- **v2 目标**：Geist Sans + Geist Mono + Noto Sans SC

### 圆角

- 输入/按钮：12px · 卡片：16px · 容器：20px

### 组件实现

- **App**：`frontend/src/components/ui/*` 为唯一交互真源；`runpod-theme.css` 为 layout token
- **Website**：`src/components/ui/*`（shadcn 风格）+ Tailwind `brand` / `surface`

### 两端对齐

- 黑绿高级感 · dark-first · 骨架屏 loading · `:focus-visible` 焦点环

---

*历史全文（v1 详细规范）曾包含色彩表、间距、组件约定等；已被主规划吸收并扩展。如需 v1 原文，见 git history 本文件 2026-05-31 之前版本。*
