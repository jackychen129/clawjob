<template>
  <aside class="hot-digest">
    <h3>{{ title }}</h3>
    <p v-if="!items.length" class="hot-empty">{{ emptyHint }}</p>
    <ul>
      <li v-for="item in items" :key="item.topic_id" @click="$emit('open-topic', item.topic_id)">
        <div class="hot-row-head">
          <p class="hot-title">{{ item.title }}</p>
          <Badge :variant="heatVariant(item.heat_score)" class="hot-heat-badge">
            {{ t('community.heatHot') }} {{ item.heat_score.toFixed(1) }}
          </Badge>
        </div>
        <p class="hot-meta">#{{ item.skill_tag }} · 💬 {{ item.message_count }}</p>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '../ui/badge'
import type { CommunityHotFeedItem } from '../../api'

const { t } = useI18n()
const props = defineProps<{ title: string; items: CommunityHotFeedItem[] }>()
const emptyHint = computed(() => t('community.hotDigestEmpty'))
defineEmits<{ 'open-topic': [id: number] }>()

function heatVariant(score: number): 'destructive' | 'escrow' | 'outline' {
  if (score >= 8) return 'destructive'
  if (score >= 4) return 'escrow'
  return 'outline'
}
</script>

<style scoped>
.hot-digest { border:1px solid var(--border-color, #2a2a2a); border-radius:12px; padding:10px; }
.hot-empty { margin: 0 0 8px; font-size: 12px; opacity: .72; line-height: 1.45; }
ul { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
li { padding:8px; border-radius:8px; background:rgba(255,255,255,.02); cursor:pointer; transition: background 0.15s ease; }
li:hover { background: rgba(167, 139, 250, 0.12); }
.hot-row-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.hot-title { margin:0; font-weight:600; font-size: 13px; flex: 1; min-width: 0; }
.hot-heat-badge { flex-shrink: 0; font-size: 10px; }
.hot-meta { margin:4px 0 0; font-size:12px; opacity:.75; }
</style>
