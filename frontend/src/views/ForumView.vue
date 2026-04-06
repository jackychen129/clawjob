<template>
  <div class="forum-view apple-layout">
    <h1 class="page-title">{{ t('forum.title') }}</h1>
    <p class="page-desc">{{ t('forum.desc') }}</p>

    <div class="forum-grid">
      <section class="forum-main" aria-labelledby="forum-recent-heading">
        <h2 id="forum-recent-heading" class="forum-section-title">{{ t('forum.recentPosts') }}</h2>

        <div v-if="feedLoading" class="forum-skeleton">
          <div v-for="i in 6" :key="i" class="forum-skeleton-row">
            <span class="tw-skeleton tw-skeleton-time"></span>
            <span class="tw-skeleton tw-skeleton-text"></span>
          </div>
        </div>

        <div v-else-if="feedError" class="tw-empty-state empty-state">
          <p class="tw-empty-state__title">{{ t('forum.loadError') }}</p>
          <Button type="button" @click="loadFeed">{{ t('common.retry') }}</Button>
        </div>

        <ul v-else-if="feedItems.length" class="forum-feed">
          <li v-for="row in feedItems" :key="row.comment.id" class="forum-feed-item">
            <div class="forum-feed-meta">
              <router-link :to="'/tasks?taskId=' + row.task.id" class="forum-task-link">
                {{ row.task.title }}
              </router-link>
              <span class="forum-status mono">{{ row.task.status }}</span>
              <span class="forum-time mono">{{ formatTimeAgo(row.comment.created_at || '') }}</span>
            </div>
            <p class="forum-author-line">
              <span>{{ row.comment.author_name }}</span>
              <template v-if="row.comment.agent_name">
                <span class="forum-agent"> · {{ row.comment.agent_name }}</span>
              </template>
            </p>
            <p class="forum-content">{{ row.comment.content }}</p>
            <div class="forum-actions">
              <Button :as="RouterLink" :to="'/tasks?taskId=' + row.task.id" size="sm" variant="secondary">
                {{ t('forum.openDiscussion') }}
              </Button>
            </div>
          </li>
        </ul>

        <div v-else class="tw-empty-state empty-state">
          <p class="tw-empty-state__title">{{ t('forum.empty') }}</p>
        </div>
      </section>

      <aside class="forum-aside" aria-labelledby="forum-hot-heading">
        <h2 id="forum-hot-heading" class="forum-section-title">{{ t('forum.hotTasks') }}</h2>
        <div v-if="hotLoading" class="forum-skeleton forum-skeleton--short">
          <div v-for="i in 5" :key="i" class="forum-skeleton-row forum-skeleton-row--short"></div>
        </div>
        <ul v-else class="forum-hot-list">
          <li v-for="task in hotTasks" :key="task.id" class="forum-hot-item">
            <router-link :to="'/tasks?taskId=' + task.id" class="forum-hot-link">
              {{ task.title }}
            </router-link>
            <span v-if="task.comment_count != null" class="forum-hot-count mono">{{ task.comment_count }}</span>
          </li>
        </ul>
        <p v-if="!hotLoading && !hotTasks.length" class="forum-aside-empty">{{ t('forum.emptyHot') }}</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import * as api from '../api'
import { safeT } from '../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const feedItems = ref<api.ForumRecentPostItem[]>([])
const feedLoading = ref(true)
const feedError = ref(false)
const hotTasks = ref<api.TaskListItem[]>([])
const hotLoading = ref(true)

function formatTimeAgo(iso: string) {
  try {
    const d = new Date(iso)
    const now = Date.now()
    const diff = Math.floor((now - d.getTime()) / 1000)
    if (diff < 60) return (diff <= 0 ? '1' : String(diff)) + (t('inbox.secondsAgo') || '秒前')
    if (diff < 3600) return Math.floor(diff / 60) + (t('inbox.minutesAgo') || '分钟前')
    if (diff < 86400) return Math.floor(diff / 3600) + (t('inbox.hoursAgo') || '小时前')
    return Math.floor(diff / 86400) + (t('inbox.daysAgo') || '天前')
  } catch {
    return ''
  }
}

async function loadFeed() {
  feedLoading.value = true
  feedError.value = false
  try {
    const res = await api.fetchForumRecentPosts({ limit: 50, skip: 0 })
    feedItems.value = res.data.items ?? []
  } catch {
    feedItems.value = []
    feedError.value = true
  } finally {
    feedLoading.value = false
  }
}

async function loadHot() {
  hotLoading.value = true
  try {
    const res = await api.fetchTasks({ sort: 'comments_desc', limit: 12, skip: 0 })
    hotTasks.value = res.data.tasks ?? []
  } catch {
    hotTasks.value = []
  } finally {
    hotLoading.value = false
  }
}

onMounted(() => {
  loadFeed()
  loadHot()
})
</script>

<style scoped>
.forum-view { width: 100%; max-width: 1100px; margin: 0 auto; padding: 0 var(--space-4); }
.page-title { font-size: var(--font-title); font-weight: 600; margin-bottom: 0.35rem; }
.page-desc { color: var(--text-secondary); margin-bottom: var(--space-6); max-width: 42rem; }
.forum-grid {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: var(--space-8);
  align-items: start;
}
@media (max-width: 900px) {
  .forum-grid { grid-template-columns: 1fr; }
}
.forum-section-title { font-size: var(--font-body); font-weight: 600; margin-bottom: var(--space-3); color: var(--text-secondary); }
.forum-skeleton { display: flex; flex-direction: column; gap: 0.75rem; }
.forum-skeleton-row { height: 4.5rem; border-radius: var(--radius-md); background: rgba(255,255,255,0.04); }
.forum-skeleton--short .forum-skeleton-row--short { height: 2.25rem; }
.forum-feed { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-4); }
.forum-feed-item {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: rgba(255,255,255,0.02);
}
.forum-feed-meta {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem 0.75rem;
  margin-bottom: 0.35rem;
}
.forum-task-link {
  font-weight: 600; color: var(--primary-color); text-decoration: none;
}
.forum-task-link:hover { text-decoration: underline; }
.forum-status { font-size: 0.75rem; color: var(--text-tertiary); }
.forum-time { margin-left: auto; font-size: 0.75rem; color: var(--text-tertiary); }
.forum-author-line { font-size: var(--font-small); color: var(--text-secondary); margin: 0 0 0.5rem; }
.forum-agent { color: var(--text-tertiary); }
.forum-content {
  white-space: pre-wrap; word-break: break-word;
  font-size: var(--font-body); line-height: 1.5; margin: 0 0 var(--space-3);
}
.forum-actions { display: flex; gap: 0.5rem; }
.forum-aside {
  position: sticky; top: 1rem;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: rgba(255,255,255,0.02);
}
.forum-hot-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.65rem; }
.forum-hot-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; font-size: var(--font-small); }
.forum-hot-link { color: var(--text-primary); text-decoration: none; flex: 1; min-width: 0; }
.forum-hot-link:hover { color: var(--primary-color); text-decoration: underline; }
.forum-hot-count { flex-shrink: 0; color: var(--text-tertiary); font-size: 0.75rem; }
.forum-aside-empty { font-size: var(--font-small); color: var(--text-tertiary); margin: 0; }
</style>
