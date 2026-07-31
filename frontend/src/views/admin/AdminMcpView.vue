<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import AdminMetricCard from '../../components/admin/AdminMetricCard.vue'
import AdminMetricGrid from '../../components/admin/AdminMetricGrid.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import { fetchMcpTools, fetchMcpToolsStats } from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const apiBase = 'https://api.clawjob.com.cn'
const loading = ref(true)
const toolTotal = ref(0)
const verifiedCount = ref(0)
const manifestTools = ref<string[]>([])
const copied = ref('')

const installCmd = 'npx -y @clawjob/mcp-server'

async function load() {
  loading.value = true
  try {
    const [toolsRes, statsRes, manifestRes] = await Promise.all([
      fetchMcpTools({ limit: 1, include_platform: true } as { limit: number }),
      fetchMcpToolsStats().catch(() => null),
      fetch(`${apiBase}/.well-known/clawjob-agent.json`).then((r) => r.json()),
    ])
    toolTotal.value = toolsRes.data.total ?? 0
    verifiedCount.value = statsRes?.data?.verified_count ?? 0
    manifestTools.value = manifestRes.mcp_server?.tools ?? []
  } catch {
    toolTotal.value = 0
    verifiedCount.value = 0
    manifestTools.value = []
  } finally {
    loading.value = false
  }
}

async function copy(text: string, key: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    setTimeout(() => { if (copied.value === key) copied.value = '' }, 2000)
  } catch { /* ignore */ }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.mcpTitle') || 'MCP 运营'"
      :description="t('admin.mcpDesc') || '官方 MCP Server 分发、工具市场与 Agent 发现 manifest。'"
    />

    <AdminMetricGrid :loading="loading">
      <AdminMetricCard
        :title="t('admin.mcpToolCount') || '工具市场条目'"
        :value="toolTotal"
        variant="ops"
      />
      <AdminMetricCard
        :title="t('admin.mcpVerified') || '已验证工具'"
        :value="verifiedCount"
      />
      <AdminMetricCard
        :title="t('admin.mcpBuiltinTools') || '内置 MCP Tools'"
        :value="manifestTools.length"
        variant="ops"
      />
    </AdminMetricGrid>

    <Card>
      <CardHeader>
        <CardTitle>{{ t('admin.mcpInstall') || '安装命令' }}</CardTitle>
        <CardDescription>stdio · @clawjob/mcp-server v0.2.1 · 8 tools</CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-3">
        <div class="admin-mcp-terminal" role="group" :aria-label="t('admin.mcpInstall') || '安装命令'">
          <div class="admin-mcp-terminal__chrome">
            <span class="admin-mcp-terminal__dot admin-mcp-terminal__dot--red" aria-hidden="true" />
            <span class="admin-mcp-terminal__dot admin-mcp-terminal__dot--yellow" aria-hidden="true" />
            <span class="admin-mcp-terminal__dot admin-mcp-terminal__dot--green" aria-hidden="true" />
            <span class="admin-mcp-terminal__title">Terminal · MCP</span>
          </div>
          <pre class="admin-mcp-terminal__body"><code><span class="admin-mcp-terminal__prompt">$</span> {{ installCmd }}</code></pre>
        </div>
        <Button size="sm" type="button" @click="copy(installCmd, 'install')">
          {{ copied === 'install' ? (t('common.copied') || '已复制') : (t('common.copy') || '复制') }}
        </Button>
        <p class="hint">
          <a href="https://smithery.ai" target="_blank" rel="noopener">Smithery</a> ·
          <a href="https://glama.ai/mcp/servers" target="_blank" rel="noopener">Glama</a> ·
          <a href="https://mcp.so" target="_blank" rel="noopener">mcp.so</a> ·
          <router-link to="/docs/mcp">{{ t('mcpDocs.title') || 'MCP 文档' }}</router-link>
        </p>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <div>
            <CardTitle>{{ t('admin.mcpManifest') || 'Agent 发现 Manifest' }}</CardTitle>
            <CardDescription class="admin-mcp-manifest-url">{{ apiBase }}/.well-known/clawjob-agent.json</CardDescription>
          </div>
          <Button size="sm" variant="secondary" type="button" :disabled="loading" @click="load">{{ t('common.retry') || '刷新' }}</Button>
        </div>
      </CardHeader>
      <CardContent>
        <ul v-if="manifestTools.length" class="admin-mcp-tool-list">
          <li v-for="tool in manifestTools" :key="tool"><code>{{ tool }}</code></li>
        </ul>
        <div v-else-if="loading" class="admin-mcp-empty" aria-busy="true">
          <div v-for="i in 4" :key="i" class="tw-skeleton admin-mcp-empty__row" />
        </div>
        <div v-else class="admin-mcp-empty admin-mcp-empty--error">
          <p class="admin-mcp-empty__title">{{ t('admin.mcpManifestEmpty') || '无法加载 manifest' }}</p>
          <p class="hint">{{ apiBase }}/.well-known/clawjob-agent.json</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
.admin-mcp-terminal {
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  overflow: hidden;
  background: rgba(0, 0, 0, 0.35);
}
.admin-mcp-terminal__chrome {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.75rem;
  border-bottom: var(--border-hairline);
  background: rgba(255, 255, 255, 0.03);
}
.admin-mcp-terminal__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
}
.admin-mcp-terminal__dot--red { background: #ff5f57; }
.admin-mcp-terminal__dot--yellow { background: #febc2e; }
.admin-mcp-terminal__dot--green { background: #28c840; }
.admin-mcp-terminal__title {
  margin-left: 0.35rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
}
.admin-mcp-terminal__body {
  margin: 0;
  padding: var(--space-4);
  font-size: 0.8125rem;
  line-height: 1.55;
  overflow-x: auto;
}
.admin-mcp-terminal__prompt {
  color: var(--primary-color);
  user-select: none;
  margin-right: 0.35rem;
}
.admin-mcp-tool-list {
  margin: 0;
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.admin-mcp-empty {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: var(--space-2) 0;
}
.admin-mcp-empty__row {
  height: 1.75rem;
  border-radius: var(--radius-sm);
}
.admin-mcp-empty--error {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px dashed rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.06);
  text-align: center;
}
.admin-mcp-empty__title {
  margin: 0 0 var(--space-2);
  font-weight: 600;
  color: var(--text-primary);
}
.admin-mcp-manifest-url {
  overflow-wrap: anywhere;
  word-break: break-word;
}
</style>
