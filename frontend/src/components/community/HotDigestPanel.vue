<template>
  <aside class="hot-digest">
    <h3>{{ title }}</h3>
    <p v-if="!items.length" class="hot-empty">{{ emptyHint }}</p>
    <ul>
      <li v-for="item in items" :key="item.topic_id" @click="$emit('open-topic', item.topic_id)">
        <p class="hot-title">{{ item.title }}</p>
        <p class="hot-meta">#{{ item.skill_tag }} · 🔥 {{ item.heat_score.toFixed(1) }} · 💬 {{ item.message_count }}</p>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CommunityHotFeedItem } from '../../api'

const { t } = useI18n()
const props = defineProps<{ title: string; items: CommunityHotFeedItem[] }>()
const emptyHint = computed(() => t('community.hotDigestEmpty'))
defineEmits<{ 'open-topic': [id: number] }>()
</script>

<style scoped>
.hot-digest { border:1px solid var(--border-color, #2a2a2a); border-radius:12px; padding:10px; }
.hot-empty { margin: 0 0 8px; font-size: 12px; opacity: .72; line-height: 1.45; }
ul { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
li { padding:8px; border-radius:8px; background:rgba(255,255,255,.02); cursor:pointer; }
.hot-title { margin:0; font-weight:600; }
.hot-meta { margin:4px 0 0; font-size:12px; opacity:.75; }
</style>
