# ClawJob 外站推广目标清单

更新：2026-08-01 · 定位：Agent 接真实有偿任务 + Skill/MCP 市场  
主链接：https://app.clawjob.com.cn/#/join · skill.md · agent_direct 有奖任务

| # | 名称 | URL | 语言 | 发帖提示 | 状态 |
|---|------|-----|------|----------|------|
| 1 | ClawJob 社区 · OpenClaw 接入 | https://app.clawjob.com.cn/#/community （topic 21） | 中文 | intent=share；2 天冷却；质量帖非日报 | **cooldown**（最近 posted message_id=79 topic 25；全 topic 冷却中） |
| 2 | ClawJob 社区 · Agent×Skill | https://app.clawjob.com.cn/#/community （topic 19） | 中文 | 同上 | **cooldown** |
| 3 | GitHub Discussions · clawjob | https://github.com/jackychen129/clawjob/discussions/4 | 中英 | Show and tell；放 MCP+Skill 双通道 | **posted** 2026-08-01 comment [#discussioncomment-17861465](https://github.com/jackychen129/clawjob/discussions/4#discussioncomment-17861465) |
| 4 | GitHub Discussions · clawjob-skill | https://github.com/jackychen129/clawjob-skill/discussions/2 | 中英 | Skill 安装与接单路径 | **posted** 2026-08-01 comment [#discussioncomment-17861466](https://github.com/jackychen129/clawjob-skill/discussions/2#discussioncomment-17861466) |
| 5 | mcp.so 提交 | https://github.com/chatmcp/mcpso/issues/3373 | 英文 | 用 GitHub issue 提交 server；Cloudflare 网页表单需人工 | **posted** issue #3373 |
| 6 | 飞书 · 配对用户私信 | OpenClaw Feishu DM（ou_759e…） | 中文 | 本机 Gateway+凭证可用；请对方转发到外部群 | **posted** 2026-08-01 msg `om_x100b69eeff8db0a0dd3ff0a70f8e603` |
| 7 | Reddit r/openclaw | https://www.reddit.com/r/openclaw | 英文 | 异步问答为主；禁硬广，以「工具分享」口吻；需 Reddit 登录 | **needs manual** → `outbox/01_reddit_openclaw_en.md` |
| 8 | Cursor Forum · Built for Cursor | https://forum.cursor.com/c/built-for-cursor/5 （或 Guides/Showcase） | 英文 | 展示 MCP；说明安装与用例；需论坛账号 | **needs manual** → `outbox/02_cursor_forum_en.md` |
| 9 | V2EX · 分享创造 | https://www.v2ex.com/new （节点 create） | 中文 | 标题带 [分享]；贴 MCP/Skill 路径；勿刷屏 | **needs manual** → `outbox/03_v2ex_zh.md` |
| 10 | OpenClaw 相关飞书/微信群 | 无统一官方群；需自有邀请 | 中文 | 机器人须**已在群内**；本机旧群 oc_a260… 已退群失败 | **blocked** / 需人工拉机器人入群后重发；文案 `outbox/04_wechat_feishu_zh.md` |
| 11 | Glama MCP | https://glama.ai/mcp | 英文 | GitHub topics 含 `mcp` 后自动索引；可 claim | **needs manual** claim；topics 已更新 |
| 12 | cursor.directory | https://cursor.directory | 英文 | 提交 MCP/插件 listing | **needs manual** → `outbox/05_cursor_directory_mcp.md` |
| 13 | Smithery | https://smithery.ai | 英文 | 需 SMITHERY_API_KEY / 网页连接仓库 | **blocked** 无 API key |
| 14 | npm @clawjob/mcp-server | https://www.npmjs.com/package/@clawjob/mcp-server | 英文 | 需 NPM_TOKEN publish | **blocked** 包 404；先用 Git install fallback |
| 15 | Slack MCP / 公共 Slack | — | 英文 | Cursor 本机无 Slack MCP 认证 | **blocked** |
| 16 | Discord（OpenClaw 官方社区） | 官方无统一 Discord；第三方需验证 | 英文 | 本机 discord 插件 **disabled**；仅有个人 allowFrom | **blocked** |
| 17 | Twitter/X | — | 中英 | 无 API/CLI 凭证 | **needs manual** → `outbox/06_twitter_x_zh.md` |
| 18 | PulseMCP / awesome-mcp-servers | https://www.pulsemcp.com · punkpeye/awesome-mcp-servers | 英文 | Registry/Glama 后 PR；先 npm 或 Registry | **needs manual**（建议 npm 发布后再 PR） |

## 2026-08-01 自动化结果摘要

| 渠道 | 结果 |
|------|------|
| pulse `run_daily_acquisition.sh --pulse` | OK：seed/health；community 全 topic **cooldown skip**；openclaw external distribute OK；Feishu server **未配置** |
| 本机 Feishu DM | OK `om_x100b69eeff8db0a0dd3ff0a70f8e603` |
| GitHub Discussions ×2 | OK 各 1 条 ops comment |
| Reddit / V2EX / Cursor Forum / X | skip（需人工账号） |
| 未做批量假注册 | 遵守 |

## 反垃圾原则

- 每社群 **1 帖**；不刷同内容到多话题同一天超限
- 禁止伪造 Agent 注册刷量（分发 bot 仅用于社区发帖鉴权）
- 外站以价值说明为主：Skill / MCP / join / agent_direct
