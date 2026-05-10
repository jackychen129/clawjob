<template>
  <section class="rich-composer">
    <div class="toolbar">
      <button type="button" @click="wrap('**', '**')"><b>B</b></button>
      <button type="button" @click="wrap('`', '`')">{{ t('community.toolbarCode') }}</button>
      <button type="button" @click="wrap('> ', '')">{{ t('community.toolbarQuote') }}</button>
      <button type="button" @click="wrap('- ', '')">{{ t('community.toolbarBullet') }}</button>
    </div>
    <textarea
      ref="composerTextarea"
      v-model="content"
      :disabled="disabled"
      rows="5"
      class="input composer-text"
      :placeholder="placeholder"
      @blur="onBlur"
    />
    <div v-if="replyToId" class="reply-banner">
      <span>{{ t('community.replyingToLabel') }} #{{ replyToId }}: {{ replyToSummary || '' }}</span>
      <button type="button" class="btn-link" @click="$emit('cancel-reply')">{{ t('community.cancelReply') }}</button>
    </div>
    <div class="media-input-row">
      <select v-model="pendingKind" :disabled="disabled" class="input media-kind">
        <option value="image">{{ t('community.kindImage') }}</option>
        <option value="file">{{ t('community.kindFile') }}</option>
        <option value="audio">{{ t('community.kindAudio') }}</option>
        <option value="video">{{ t('community.kindVideo') }}</option>
        <option value="link">{{ t('community.kindLink') }}</option>
      </select>
      <input
        v-model="pendingUrl"
        :disabled="disabled"
        class="input media-url"
        :placeholder="mediaPlaceholder"
      />
      <button type="button" class="btn-ghost" :disabled="disabled || !pendingUrl.trim()" @click="addMedia">
        {{ t('community.addMedia') }}
      </button>
    </div>
    <ul v-if="attachments.length" class="media-list">
      <li v-for="(a, idx) in attachments" :key="`${a.kind}-${a.url}-${idx}`">
        <span>[{{ a.kind }}] {{ a.url }}</span>
        <button type="button" class="btn-link" @click="removeMedia(idx)">x</button>
      </li>
    </ul>
    <div class="intent-row">
      <label class="intent-label">{{ t('community.intentLabel') }}</label>
      <select v-model="intent" :disabled="disabled" class="input intent-select">
        <option value="chat">{{ t('community.intentChat') }}</option>
        <option value="tip">{{ t('community.intentTip') }}</option>
        <option value="question">{{ t('community.intentQuestion') }}</option>
        <option value="resource">{{ t('community.intentResource') }}</option>
        <option value="recap">{{ t('community.intentRecap') }}</option>
      </select>
    </div>
    <div class="composer-actions">
      <button type="button" class="btn" :disabled="disabled || loading || (!content.trim() && !attachments.length)" @click="submit">
        {{ submitText }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CommunityAttachment } from '../../api'

const { t } = useI18n()

const props = defineProps<{
  disabled: boolean
  loading: boolean
  placeholder: string
  mediaPlaceholder: string
  submitText: string
  replyToId?: number | null
  replyToSummary?: string
  /** 父组件递增 nonce 并设置 text，可将模板填入输入框 */
  draftNudge?: { text: string; nonce: number } | null
}>()
const emit = defineEmits<{
  submit: [payload: { content: string; attachments: CommunityAttachment[]; intent: string }]
  'cancel-reply': []
  typing: [payload: { active: boolean }]
}>()
const content = ref('')
const composerTextarea = ref<HTMLTextAreaElement | null>(null)
const intent = ref('chat')
const pendingKind = ref<CommunityAttachment['kind']>('image')
const pendingUrl = ref('')
const attachments = ref<CommunityAttachment[]>([])
let debounceTyping: ReturnType<typeof setTimeout> | null = null

function scheduleTypingPing() {
  if (props.disabled) return
  if (debounceTyping) clearTimeout(debounceTyping)
  debounceTyping = setTimeout(() => {
    emit('typing', { active: content.value.trim().length > 0 })
    debounceTyping = null
  }, 450)
}

watch(content, () => scheduleTypingPing())

watch(
  () => props.disabled,
  (v) => {
    if (v) emit('typing', { active: false })
  },
)

watch(
  () => props.draftNudge,
  (v) => {
    if (!v?.text || !v.nonce || props.disabled) return
    content.value = v.text
    nextTick(() => composerTextarea.value?.focus())
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (debounceTyping) clearTimeout(debounceTyping)
  emit('typing', { active: false })
})

function onBlur() {
  emit('typing', { active: false })
}

function wrap(prefix: string, suffix: string) {
  content.value = `${prefix}${content.value}${suffix}`
}

function submit() {
  const trimmed = content.value.trim()
  if (!trimmed && !attachments.value.length) return
  emit('typing', { active: false })
  emit('submit', {
    content: trimmed,
    attachments: attachments.value.slice(0, 10),
    intent: intent.value,
  })
  content.value = ''
  attachments.value = []
  pendingUrl.value = ''
}

function addMedia() {
  const url = pendingUrl.value.trim()
  if (!url) return
  if (!/^https?:\/\//i.test(url)) return
  attachments.value = [...attachments.value, { kind: pendingKind.value, url }].slice(0, 10)
  pendingUrl.value = ''
}

function removeMedia(idx: number) {
  attachments.value = attachments.value.filter((_, i) => i !== idx)
}
</script>

<style scoped>
.rich-composer { border:1px solid var(--border-color, #2a2a2a); border-radius:12px; padding:10px; }
.toolbar { display:flex; gap:6px; margin-bottom:8px; }
.toolbar button { border:1px solid rgba(255,255,255,.2); background:transparent; color:inherit; border-radius:8px; padding:4px 8px; cursor:pointer; }
.composer-text { width:100%; resize:vertical; }
.reply-banner { margin-top:8px; display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:12px; padding:6px 8px; border-radius:8px; background:rgba(79,70,229,.12); }
.media-input-row { margin-top:8px; display:flex; gap:8px; align-items:center; }
.media-kind { width:110px; }
.media-url { flex:1; }
.btn-ghost { border:1px solid rgba(255,255,255,.25); background:transparent; color:inherit; border-radius:8px; padding:7px 10px; cursor:pointer; }
.media-list { list-style:none; margin:8px 0 0; padding:0; display:flex; flex-direction:column; gap:6px; }
.media-list li { display:flex; justify-content:space-between; gap:10px; font-size:12px; padding:6px 8px; border-radius:8px; background:rgba(255,255,255,.03); }
.intent-row { margin-top:10px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.intent-label { font-size:12px; opacity:.85; margin:0; }
.intent-select { max-width:220px; min-width:140px; font-size:13px; }
.btn-link { border:0; background:transparent; color:#a78bfa; cursor:pointer; }
.composer-actions { display:flex; justify-content:flex-end; margin-top:8px; }
.btn { border:0; border-radius:8px; background:#4f46e5; color:white; padding:8px 14px; cursor:pointer; }
</style>
