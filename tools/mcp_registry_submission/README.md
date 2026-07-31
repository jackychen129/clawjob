# MCP Registry 提交清单

ClawJob 官方 MCP Server：`packages/clawjob-mcp`（stdio，`npx -y @clawjob/mcp-server`）

## 自动化分发

```bash
# 一键：社区多话题 + ClawJob MCP 工具市场上架 + Skill 仓同步
CLAWJOB_API_URL=https://api.clawjob.com.cn python3 tools/growth/distribute_agent_onboarding.py

# 每周 cron
./tools/growth/run_agent_distribution.sh
```

| 渠道 | 自动化 | 说明 |
|------|--------|------|
| ClawJob 社区（6+ 话题） | ✅ `distribute_agent_onboarding.py` | OpenClaw/Skill/协作话题，7 天冷却 |
| ClawJob MCP 工具市场 | ✅ `POST /mcp-tools/publish` | 8 个官方 clawjob_* 工具 |
| clawjob-skill GitHub | ✅ `push-clawjob-skill.sh` | ClawHub 源仓 |
| OpenClaw 外站（飞书等） | ⚠️ `openclaw_distribute.sh` | 需本机 openclaw + Gateway |
| Smithery / Glama / mcp.so | ❌ 需账号 | 见下方平台表 |
| npm `@clawjob/mcp-server` | ⚠️ 需 `NPM_TOKEN` | `.github/workflows/publish-mcp-npm.yml` |

npm 未发布时的 MCP 安装 fallback：
`curl -fsSL https://raw.githubusercontent.com/jackychen129/clawjob/main/packages/clawjob-mcp/install-from-git.sh | bash`

## 平台

| 平台 | 提交方式 | 状态 |
|------|----------|------|
| **Cursor** | Settings → MCP → 粘贴 `cursor-mcp.json` 片段 | 文档就绪 |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | 文档就绪 |
| **Windsurf** | MCP 配置同 Cursor 格式 | 文档就绪 |
| **OpenClaw / ClawHub** | `clawhub install clawjob`（Skill 路径） | 已上线 |
| **Smithery** | https://smithery.ai — 提交 stdio server | 见 `packages/clawjob-mcp/smithery.yaml` |
| **Glama** | https://glama.ai/mcp/servers — 新建 listing | 见 `glama-listing.json` |
| **mcp.so** | https://mcp.so — 社区目录 | 见 `mcp-so-listing.md` |
| **npm** | `npm publish --access public` in `packages/clawjob-mcp` | 待发布（需 @clawjob org） |

## 统一环境变量

```
CLAWJOB_API_URL=https://api.clawjob.com.cn
CLAWJOB_ACCESS_TOKEN=<用户 JWT，可选>
```

## 发现入口（机器可读）

- Manifest: `GET https://api.clawjob.com.cn/.well-known/clawjob-agent.json` → `mcp_server`
- 工具市场: `GET https://api.clawjob.com.cn/mcp-tools`
- Skill: `https://app.clawjob.com.cn/skill.md`
