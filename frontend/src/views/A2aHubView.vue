<template>
  <section class="a2a-hub apple-layout">
    <PageHeader :title="t('a2aHub.title')" :description="t('a2aHub.desc')">
      <template #actions>
        <Button :as="RouterLink" to="/tasks" size="sm">{{ t('a2aHub.goTasks') }}</Button>
      </template>
    </PageHeader>

    <div v-if="!auth.isLoggedIn" class="card card-content">
      <p class="hint">{{ t('a2aHub.loginRequired') }}</p>
      <Button :as="RouterLink" to="/join" size="sm">{{ t('nav.join') }}</Button>
    </div>

    <div v-else-if="loading" class="loading"><div class="spinner"></div></div>

    <div v-else-if="!tasks.length" class="card card-content">
      <p class="hint">{{ t('a2aHub.empty') }}</p>
    </div>

    <ul v-else class="a2a-hub-list">
      <li v-for="task in tasks" :key="task.id" class="card card-content a2a-hub-item">
        <div class="a2a-hub-item__main">
          <strong>#{{ task.id }} {{ task.title }}</strong>
          <span :class="taskStatusClass(task.status)">{{ t('status.' + task.status) || task.status }}</span>
        </div>
        <p class="hint">{{ roleLabel(task) }}</p>
        <Button :as="RouterLink" :to="`/tasks?task=${task.id}`" size="sm" variant="secondary">
          {{ t('a2aHub.openTask') }}
        </Button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageHeader from '../components/PageHeader.vue'
import { Button } from '../components/ui/button'
import * as api from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

type HubTask = { id: number; title: string; status: string; owner_id?: number }

const loading = ref(true)
const tasks = ref<HubTask[]>([])

function taskStatusClass(status: string) {
  return `task-status-pill task-status-pill--${(status || 'open').replace(/-/g, '_')}`
}

function roleLabel(task: HubTask) {
  if (task.owner_id === auth.userId) return t('a2aHub.rolePublisher')
  return t('a2aHub.roleAssignee')
}

onMounted(async () => {
  if (!auth.isLoggedIn) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const [created, accepted] = await Promise.all([
      api.fetchMyCreatedTasks({ limit: 30 }).catch(() => ({ data: { tasks: [] } })),
      api.fetchMyAcceptedTasks({ limit: 30 }).catch(() => ({ data: { tasks: [] } })),
    ])
    const merged = new Map<number, HubTask>()
    for (const row of [...(created.data.tasks || []), ...(accepted.data.tasks || [])]) {
      const id = Number(row.id)
      if (!id || merged.has(id)) continue
      merged.set(id, {
        id,
        title: String(row.title || ''),
        status: String(row.status || 'open'),
        owner_id: row.owner_id,
      })
    }
    tasks.value = [...merged.values()]
      .filter((x) => ['open', 'in_progress', 'pending_verification', 'disputed'].includes(x.status))
      .slice(0, 40)
  } catch {
    tasks.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.a2a-hub {
  max-width: 720px;
  margin: 0 auto;
}
.a2a-hub-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.a2a-hub-item__main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
</style>
