<template>
  <div class="discover-view apple-layout">
    <PageHeader
      :title="t('discover.title')"
      :description="t('discover.desc')"
    />

    <div class="discover-tabs" role="tablist" :aria-label="t('discover.tabAria')">
      <router-link
        to="/discover/agents"
        class="discover-tab"
        :class="{ active: activeTab === 'agents' }"
        role="tab"
        :aria-selected="activeTab === 'agents'"
      >
        {{ t('discover.tabAgents') }}
      </router-link>
      <router-link
        to="/discover/ranks"
        class="discover-tab"
        :class="{ active: activeTab === 'ranks' }"
        role="tab"
        :aria-selected="activeTab === 'ranks'"
      >
        {{ t('discover.tabRanks') }}
      </router-link>
    </div>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageHeader from '../components/PageHeader.vue'

const { t } = useI18n()
const route = useRoute()

const activeTab = computed(() => {
  if (route.path.includes('/ranks')) return 'ranks'
  return 'agents'
})
</script>

<style scoped>
.discover-tabs {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border-hairline, rgba(255, 255, 255, 0.06));
  padding-bottom: var(--space-2);
}

.discover-tab {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md, 8px);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary, #a1a1aa);
  text-decoration: none;
  transition: color 0.15s, background 0.15s;
}

.discover-tab:hover {
  color: var(--color-text-primary, #fafafa);
  background: rgba(255, 255, 255, 0.04);
}

.discover-tab.active {
  color: var(--color-brand-primary, #22c55e);
  background: rgba(34, 197, 94, 0.1);
}
</style>
