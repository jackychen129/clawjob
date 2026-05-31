<template>
  <aside class="topic-list">
    <div class="topic-list-head">
      <h3>{{ title }}</h3>
      <span class="topic-list-count">{{ items.length }}</span>
    </div>
    <div class="topic-list-search">
      <input v-model="innerQuery" type="search" :placeholder="searchPlaceholder" class="input" @input="$emit('search', innerQuery)" />
    </div>
    <p v-if="loading" class="topic-loading" aria-busy="true">
      <span v-for="i in 6" :key="i" class="tw-skeleton topic-skel-row" />
    </p>
    <p v-else-if="!items.length" class="topic-empty">{{ emptyHint }}</p>
    <ul class="topic-list-items">
      <li
        v-for="topic in items"
        :key="topic.id"
        class="topic-list-item"
        :class="{ active: selectedId === topic.id }"
        @click="$emit('select', topic.id)"
      >
        <div class="topic-title">{{ topic.title }}</div>
        <div class="topic-meta">
          <span>#{{ topic.skill_tag }}</span>
          <span>🔥 {{ topic.heat_score.toFixed(1) }}</span>
          <span>💬 {{ topic.message_count || 0 }}</span>
        </div>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CommunityTopic } from '../../api'

const { t } = useI18n()
const props = defineProps<{
  items: CommunityTopic[]
  selectedId: number | null
  title: string
  searchPlaceholder: string
  query?: string
  loading?: boolean
}>()
const emptyHint = computed(() =>
  props.query?.trim() ? t('community.topicEmptySearch') : t('community.topicEmpty'),
)
defineEmits<{
  select: [id: number]
  search: [q: string]
}>()

const innerQuery = ref(props.query || '')
watch(() => props.query, (v) => { innerQuery.value = v || '' })
</script>

<style scoped>
.topic-list { border: 1px solid var(--border-color, #2a2a2a); border-radius: 12px; padding: 12px; background: rgba(255,255,255,0.02); }
.topic-list-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.topic-list-count { font-size: 12px; opacity: .7; }
.topic-list-search { margin-bottom: 8px; }
.topic-loading { display: flex; flex-direction: column; gap: 8px; margin: 0; }
.topic-skel-row { height: 2.75rem; border-radius: 10px; }
.topic-list-items { list-style:none; margin:0; padding:0; max-height: 62vh; overflow:auto; display:flex; flex-direction:column; gap:8px; }
.topic-list-item { padding: 10px; border-radius: 10px; cursor: pointer; border: 1px solid transparent; }
.topic-list-item:hover { background: rgba(255,255,255,.04); }
.topic-list-item.active { border-color: #4f46e5; background: rgba(79,70,229,.12); }
.topic-title { font-weight: 600; margin-bottom: 4px; }
.topic-meta { display:flex; gap:10px; font-size: 12px; opacity: .75; }
</style>
