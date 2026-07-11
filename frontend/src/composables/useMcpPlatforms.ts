import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

export type McpPlatformId =
  | 'cursor'
  | 'claude'
  | 'windsurf'
  | 'openclaw'
  | 'smithery'
  | 'glama'
  | 'mcp_so'

const MCP_CONFIG = {
  mcpServers: {
    clawjob: {
      command: 'npx',
      args: ['-y', '@clawjob/mcp-server'],
      env: {
        CLAWJOB_API_URL: 'https://api.clawjob.com.cn',
        CLAWJOB_ACCESS_TOKEN: '',
      },
    },
  },
}

function resolveAppOrigin(): string {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin.replace(/\/$/, '')
  }
  return 'https://clawjob.com.cn'
}

export function useMcpPlatforms() {
  const { t } = useI18n()
  const copiedId = ref<McpPlatformId | null>(null)
  const appBase = resolveAppOrigin()

  const platforms = computed(() => [
    {
      id: 'cursor' as const,
      name: 'Cursor',
      category: 'mcp' as const,
      descKey: 'agentManage.cliCursorMcp',
      configJson: JSON.stringify(MCP_CONFIG, null, 2),
      docsUrl: `${appBase}/mcp/cursor-mcp.json`,
    },
    {
      id: 'claude' as const,
      name: 'Claude Desktop',
      category: 'mcp' as const,
      descKey: 'agentManage.cliClaudeMcp',
      configJson: JSON.stringify(MCP_CONFIG, null, 2),
    },
    {
      id: 'windsurf' as const,
      name: 'Windsurf',
      category: 'mcp' as const,
      descKey: 'agentManage.cliWindsurfMcp',
      configJson: JSON.stringify(MCP_CONFIG, null, 2),
    },
    {
      id: 'openclaw' as const,
      name: String(t('agentManage.platformOpenClaw')),
      category: 'skill' as const,
      descKey: 'agentManage.cliOpenClawSkill',
      configJson: `clawhub install clawjob\n# or read ${appBase}/skill.md`,
      docsUrl: `${appBase}/#/skill`,
    },
    {
      id: 'smithery' as const,
      name: 'Smithery',
      category: 'mcp' as const,
      descKey: 'agentManage.cliSmitheryMcp',
      configJson: `npx -y @clawjob/mcp-server`,
      docsUrl: 'https://smithery.ai',
    },
    {
      id: 'glama' as const,
      name: 'Glama',
      category: 'mcp' as const,
      descKey: 'agentManage.cliGlamaMcp',
      configJson: `npx -y @clawjob/mcp-server`,
      docsUrl: 'https://glama.ai/mcp/servers',
    },
    {
      id: 'mcp_so' as const,
      name: 'mcp.so',
      category: 'mcp' as const,
      descKey: 'agentManage.cliMcpSo',
      configJson: `npx -y @clawjob/mcp-server`,
      docsUrl: 'https://mcp.so',
    },
  ])

  async function copyPlatform(id: McpPlatformId, text: string) {
    try {
      await navigator.clipboard.writeText(text)
      copiedId.value = id
      setTimeout(() => {
        copiedId.value = null
      }, 2000)
      return true
    } catch {
      return false
    }
  }

  return { platforms, copiedId, copyPlatform, mcpConfigJson: JSON.stringify(MCP_CONFIG, null, 2) }
}
