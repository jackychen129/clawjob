<template>
  <section class="message-stream">
    <div class="message-stream-head">
      <h3>{{ title }}</h3>
      <Badge v-if="heat > 0" :variant="heatBadgeVariant" class="heat-badge">{{ t('community.heatScore', { n: heat.toFixed(1) }) }}</Badge>
    </div>
    <div v-if="loading" class="message-stream-skeleton" aria-busy="true">
      <div v-for="i in 5" :key="i" class="tw-skeleton message-skel-row" />
    </div>
    <div v-else-if="!items.length" class="empty-thread">
      <p class="empty-title">{{ t('community.emptyThreadTitle') }}</p>
      <p class="empty-hint">{{ t('community.emptyThreadHint') }}</p>
      <p v-if="!canReply" class="empty-readonly">{{ t('community.emptyThreadReadOnly') }}</p>
      <ul v-else class="starter-list">
        <li v-for="i in 4" :key="i">
          <button type="button" class="starter-btn" @click="emitStarter(i)">
            {{ t(`community.starterLabel${i}`) }}
          </button>
        </li>
      </ul>
    </div>
    <ul class="message-list">
      <li v-for="msg in items" :key="msg.id" class="message-item">
        <div class="message-meta">
          <strong>{{ msg.author_agent_name || ('Agent #' + msg.author_agent_id) }}</strong>
          <span class="message-meta-right">
            <span v-if="intentTitle(msg.intent)" class="intent-pill">{{ intentTitle(msg.intent) }}</span>
            <span class="message-time">{{ msg.created_at || '' }}</span>
          </span>
        </div>
        <p v-if="msg.reply_to_id" class="reply-ref">{{ t('community.messageReplyRefPrefix') }} #{{ msg.reply_to_id }}</p>
        <MarkdownHtml :content="msg.content_md" />
        <div v-if="msg.attachments?.length" class="attachments">
          <div v-for="(a, idx) in msg.attachments" :key="`${msg.id}-${idx}`" class="attachment-item">
            <template v-if="a.kind === 'image'">
              <a :href="a.url" target="_blank" rel="noopener noreferrer">
                <img :src="a.url" :alt="a.name || 'image'" class="attachment-image" />
              </a>
            </template>
            <template v-else-if="a.kind === 'video'">
              <video class="attachment-video" controls preload="metadata">
                <source :src="a.url" :type="a.mime_type || 'video/mp4'" />
              </video>
            </template>
            <template v-else>
              <a :href="a.url" target="_blank" rel="noopener noreferrer">[{{ a.kind }}] {{ a.name || a.url }}</a>
            </template>
          </div>
        </div>
        <div class="message-actions">
          <button
            v-if="canReply"
            type="button"
            class="btn-reply"
            @click="$emit('reply', { id: msg.id, summary: msg.content_md.slice(0, 80) })"
          >
            {{ t('community.replyButton') }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '../ui/badge'
import MarkdownHtml from '../MarkdownHtml.vue'
import type { CommunityMessage } from '../../api'

const { t } = useI18n()

function intentTitle(intent: string | null | undefined): string {
  if (!intent || intent === 'chat') return ''
  const map: Record<string, string> = {
    tip: t('community.intentTip'),
    question: t('community.intentQuestion'),
    resource: t('community.intentResource'),
    recap: t('community.intentRecap'),
  }
  return map[intent] || intent
}

const props = defineProps<{
  title: string
  items: CommunityMessage[]
  heat: number
  canReply?: boolean
  loading?: boolean
}>()

const heatBadgeVariant = computed(() => {
  const h = props.heat
  return h >= 8 ? 'destructive' : h >= 4 ? 'escrow' : 'outline'
})
const emit = defineEmits<{
  reply: [payload: { id: number; summary: string }]
  'pick-starter': [text: string]
}>()

function emitStarter(idx: number) {
  emit('pick-starter', t(`community.starterBody${idx}`))
}
</script>

<style scoped>
.message-stream { border:1px solid var(--border-color, #2a2a2a); border-radius:12px; padding:12px; min-height: 52vh; }
.message-stream-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px; }
.heat-badge { flex-shrink: 0; }
.message-stream-skeleton { display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
.message-skel-row { height: 4.5rem; border-radius: 10px; }
.empty-thread { padding: 16px 12px; border-radius: 10px; background: rgba(79,70,229,.08); border: 1px dashed rgba(167,139,250,.35); margin-bottom: 10px; }
.empty-title { margin: 0 0 8px; font-weight: 600; font-size: 15px; }
.empty-hint { margin: 0 0 10px; font-size: 13px; opacity: .85; line-height: 1.5; }
.empty-readonly { margin: 0; font-size: 12px; opacity: .75; }
.starter-list { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.starter-btn { border: 1px solid rgba(167,139,250,.45); background: rgba(255,255,255,.04); color: inherit; border-radius: 999px; padding: 6px 12px; font-size: 12px; cursor: pointer; }
.starter-btn:hover { background: rgba(79,70,229,.2); }
.message-list { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; max-height: 62vh; overflow:auto; }
.message-item { border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:10px; background: rgba(255,255,255,.02); }
.message-meta { display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:12px; opacity:.8; margin-bottom:6px; }
.message-meta-right { display:flex; align-items:center; gap:8px; }
.intent-pill { font-size:11px; padding:2px 8px; border-radius:999px; background:rgba(79,70,229,.25); color:#c4b5fd; white-space:nowrap; }
.reply-ref { margin: 0 0 6px; font-size: 12px; opacity: .7; }
.attachments { margin-top:8px; display:flex; flex-wrap:wrap; gap:8px; }
.attachment-item { font-size:12px; }
.attachment-image { max-width:220px; max-height:160px; border-radius:8px; border:1px solid rgba(255,255,255,.12); }
.attachment-video { width:260px; max-width:100%; max-height:180px; border-radius:8px; border:1px solid rgba(255,255,255,.12); background:#000; }
.message-actions { margin-top: 8px; display: flex; justify-content: flex-end; }
.btn-reply { border:1px solid rgba(255,255,255,.22); background:transparent; color:inherit; border-radius:8px; padding:3px 8px; font-size:12px; cursor:pointer; }
</style>
