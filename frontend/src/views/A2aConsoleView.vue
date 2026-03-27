<template>
  <section class="a2a-console">
    <h1 class="page-title">A2A Console</h1>
    <p class="page-desc">Browse my accepted tasks and inspect A2A message timelines.</p>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>
    <div v-else-if="!tasks.length" class="card empty">No accepted tasks yet.</div>
    <div v-else class="grid">
      <article v-for="t in tasks" :key="t.id" class="card task-card">
        <div class="task-card__head">
          <h3>{{ t.title }}</h3>
          <button type="button" class="btn" :disabled="messageLoadingId === t.id" @click="loadMessages(t.id)">
            {{ messageLoadingId === t.id ? 'Loading...' : 'Load A2A' }}
          </button>
        </div>
        <p class="hint">Status: <span class="mono">{{ t.status }}</span></p>
        <ul v-if="messagesMap[t.id]?.length" class="msg-list">
          <li v-for="m in messagesMap[t.id]" :key="m.id" class="msg-row">
            <span class="mono msg-kind">{{ m.kind || 'message' }}</span>
            <span class="msg-author">{{ m.agent_name || m.author_name }}</span>
            <span class="msg-content">{{ m.content }}</span>
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as api from '../api'

const loading = ref(false)
const tasks = ref<api.TaskListItem[]>([])
const messagesMap = ref<Record<number, api.TaskCommentItem[]>>({})
const messageLoadingId = ref<number | null>(null)

function reload() {
  loading.value = true
  api.fetchMyAcceptedTasks({ limit: 100 })
    .then((res) => { tasks.value = res.data.tasks || [] })
    .catch(() => { tasks.value = [] })
    .finally(() => { loading.value = false })
}

function loadMessages(taskId: number) {
  messageLoadingId.value = taskId
  api.a2aListMessages(taskId)
    .then((res) => {
      messagesMap.value = { ...messagesMap.value, [taskId]: res.data.messages || [] }
    })
    .catch(() => {
      messagesMap.value = { ...messagesMap.value, [taskId]: [] }
    })
    .finally(() => { messageLoadingId.value = null })
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.a2a-console { display: grid; gap: var(--space-5); }
.page-desc { color: var(--text-secondary); margin: 0; }
.grid { display: grid; gap: var(--space-4); }
.task-card { padding: var(--space-5); }
.task-card__head { display: flex; justify-content: space-between; gap: var(--space-3); align-items: center; }
.btn { border: var(--border-hairline); border-radius: var(--radius-md); padding: .35rem .6rem; background: rgba(255,255,255,.06); color: var(--text-primary); }
.msg-list { margin: var(--space-3) 0 0; padding: 0; list-style: none; display: grid; gap: var(--space-2); }
.msg-row { display: grid; grid-template-columns: auto auto 1fr; gap: var(--space-2); font-size: var(--font-caption); }
.msg-kind { color: var(--text-secondary); }
.msg-author { font-weight: 600; }
.msg-content { color: var(--text-secondary); }
</style>
