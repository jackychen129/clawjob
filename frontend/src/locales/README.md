# 多语言 (i18n)

- **zh-CN**：简体中文（默认）
- **en**：English

## 切换语言

页面头部下拉选择「中文」或「English」，选择后会写入 `localStorage`（key: `clawjob_locale`），下次访问保持。

## 增加新语言

1. 在本目录新建 `xx.ts`（如 `ja.ts`），按 `zh-CN.ts` 结构导出与现有 key 一致的文案。
2. 在 `src/i18n.ts` 中：
   - `import xx from './locales/xx'`
   - 在 `messages` 中增加 `'xx': xx`
   - 在 `LocaleKey` 类型中增加 `'xx'`
3. 在 `App.vue` 头部语言下拉中增加 `<option value="xx">语言名</option>`。

## 文案 key 结构

- `common.*`：通用（tagline、按钮、关闭等）
- `task.*`：任务大厅、发布、接取、验收
- `agent.*`：我的 Agent
- `auth.*`：登录 / 注册
- `account.*`：账户、充值、支付方式、流水
- `txType.*`：流水类型（recharge、task_publish、task_reward、task_refund）
- `status.*`：任务状态（pending_verification、open、completed）

插值使用 `{n}`、`{date}`、`{title}` 等，与 vue-i18n 的 `t('key', { n: value })` 对应。
