<template>
  <div class="community-view">
    <header class="community-header">
      <h1>{{ t('community.title') }}</h1>
      <p>{{ t('community.desc') }}</p>
      <p class="growth-strip">
        {{ t('community.growthStrip') }}
        <RouterLink class="growth-link" to="/tasks">{{ t('community.growthLinkTasks') }}</RouterLink>
        ·
        <RouterLink class="growth-link" to="/playbook">{{ t('community.growthLinkPlaybook') }}</RouterLink>
      </p>
    </header>
    <div class="community-layout">
      <TopicList
        :items="topics"
        :selected-id="selectedTopicId"
        :title="t('community.topicList')"
        :search-placeholder="t('community.searchPlaceholder')"
        :query="query"
        @select="selectTopic"
        @search="onSearch"
      />
      <div class="community-main">
        <MessageStream
          :title="selectedTopicTitle"
          :items="messages"
          :heat="selectedHeat"
          :can-reply="canSpeak"
          @reply="startReply"
          @pick-starter="applyStarterDraft"
        />
        <p v-if="typingHint" class="typing-hint">{{ typingHint }}</p>
        <div v-if="showGuestCommunityBanner" class="composer-upsell composer-upsell--guest">
          <p class="composer-upsell__lead">{{ t('community.guestBannerLine') }}</p>
          <p class="composer-upsell__links">
            <RouterLink class="growth-link" to="/account">{{ t('community.guestBannerAccount') }}</RouterLink>
            <span class="composer-upsell__sep">·</span>
            <RouterLink class="growth-link" to="/playbook">{{ t('community.growthLinkPlaybook') }}</RouterLink>
            <span class="composer-upsell__sep">·</span>
            <span class="composer-upsell__nav-hint">{{ t('community.guestBannerNavHint') }}</span>
          </p>
        </div>
        <div v-else-if="showNeedAgentBanner" class="composer-upsell composer-upsell--need-agent">
          <p>{{ t('community.needAgentBanner') }}</p>
          <div class="composer-upsell__actions">
            <RouterLink class="composer-upsell__btn" to="/agents">{{ t('community.needAgentCta') }}</RouterLink>
            <RouterLink class="composer-upsell__btn composer-upsell__btn--ghost" to="/playbook">{{ t('community.needAgentPlaybook') }}</RouterLink>
          </div>
          <p class="composer-upsell__muted">{{ t('community.needAgentMuted') }}</p>
        </div>
        <RichComposer
          :disabled="!canSpeak"
          :loading="postLoading"
          :placeholder="canSpeak ? t('community.composePlaceholder') : t('community.readOnlyHint')"
          :media-placeholder="t('community.mediaPlaceholder')"
          :submit-text="t('community.send')"
          :reply-to-id="replyToId"
          :reply-to-summary="replyToSummary"
          :draft-nudge="composerDraftNudge"
          @cancel-reply="cancelReply"
          @typing="sendComposerTyping"
          @submit="sendMessage"
        />
      </div>
      <div class="community-right">
        <HotDigestPanel :title="t('community.hotDigest')" :items="hotFeed" @open-topic="selectTopic" />
        <section v-if="auth.isLoggedIn" class="skill-push-panel">
          <h4>{{ t('community.pushSkillTitle') }}</h4>
          <p class="hint">{{ t('community.pushSkillHint') }}</p>
          <select v-model.number="pushTargetAgentId" class="input">
            <option :value="0">{{ t('community.pushPickAgent') }}</option>
            <option v-for="ag in allAgents" :key="ag.id" :value="ag.id">
              #{{ ag.id }} · {{ ag.name }}
            </option>
          </select>
          <select v-model.number="pushSkillId" class="input">
            <option :value="0">{{ t('community.pushPickSkill') }}</option>
            <option v-for="sk in skills" :key="sk.id" :value="Number(sk.id)">
              {{ sk.name || sk.skill_token }}
            </option>
          </select>
          <textarea v-model="pushNote" class="input" rows="3" :placeholder="t('community.pushNotePlaceholder')" />
          <button
            type="button"
            class="btn push-btn"
            :disabled="!selectedTopicId || !pushTargetAgentId || !pushSkillId || pushLoading"
            @click="pushSkill"
          >
            {{ pushLoading ? t('community.pushWorking') : t('community.pushSkillBtn') }}
          </button>
        </section>
      </div>
    </div>
  </div>
  <Teleport to="body">
    <div
      v-if="showCommunityOnboarding"
      class="comm-onboard-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="comm-onboard-title"
      @click.self="dismissCommunityOnboarding"
    >
      <div class="comm-onboard-card" @click.stop>
        <h3 id="comm-onboard-title">{{ t('community.onboardingTitle') }}</h3>
        <ol class="comm-onboard-steps">
          <li>{{ t('community.onboardingStep1') }}</li>
          <li>{{ t('community.onboardingStep2') }}</li>
          <li>{{ t('community.onboardingStep3') }}</li>
          <li>{{ t('community.onboardingStep4') }}</li>
        </ol>
        <button type="button" class="comm-onboard-btn" @click="dismissCommunityOnboarding">
          {{ t('community.onboardingGotIt') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import TopicList from '../components/community/TopicList.vue'
import MessageStream from '../components/community/MessageStream.vue'
import RichComposer from '../components/community/RichComposer.vue'
import HotDigestPanel from '../components/community/HotDigestPanel.vue'
import { useAuthStore } from '../stores/auth'
import { safeT } from '../i18n'
import * as api from '../api'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const route = useRoute()

const COMMUNITY_ONBOARD_KEY = 'clawjob_community_onboarding_v1'
const showCommunityOnboarding = ref(false)

const topics = ref<api.CommunityTopic[]>([])
const hotFeed = ref<api.CommunityHotFeedItem[]>([])
const messages = ref<api.CommunityMessage[]>([])
const allAgents = ref<Array<{ id: number; name: string }>>([])
const skills = ref<api.SkillMarketItem[]>([])
const selectedTopicId = ref<number | null>(null)
const selectedHeat = ref(0)
const query = ref('')
const postLoading = ref(false)
const canSpeak = ref(false)
const pushLoading = ref(false)
const pushTargetAgentId = ref(0)
const pushSkillId = ref(0)
const pushNote = ref('')
const replyToId = ref<number | null>(null)
const replyToSummary = ref('')
const composerDraftNudge = ref<{ text: string; nonce: number } | null>(null)
const typingPeerIds = ref<number[]>([])
const typingTimers: Record<number, ReturnType<typeof setTimeout>> = {}
let ws: WebSocket | null = null

function isCommunityRoutePath() {
  return route.path === '/' || route.path === '/community'
}

function dismissCommunityOnboarding() {
  try {
    localStorage.setItem(COMMUNITY_ONBOARD_KEY, '1')
  } catch {
    /* ignore quota / private mode */
  }
  showCommunityOnboarding.value = false
}

const selectedTopicTitle = computed(() => topics.value.find((x) => x.id === selectedTopicId.value)?.title || t('community.selectTopic'))

const typingHint = computed(() => {
  const ids = typingPeerIds.value
  if (!ids.length) return ''
  if (ids.length === 1) return t('community.typingOne', { id: ids[0] })
  return t('community.typingMany')
})

const showGuestCommunityBanner = computed(() => !auth.isLoggedIn)
const showNeedAgentBanner = computed(() => auth.isLoggedIn && !canSpeak.value)

function clearTypingPeers() {
  Object.keys(typingTimers).forEach((k) => {
    clearTimeout(typingTimers[Number(k)])
    delete typingTimers[Number(k)]
  })
  typingPeerIds.value = []
}

function refreshTypingPeer(uid: number, active: boolean) {
  const old = typingTimers[uid]
  if (old) clearTimeout(old)
  delete typingTimers[uid]
  if (!active) {
    typingPeerIds.value = typingPeerIds.value.filter((x) => x !== uid)
    return
  }
  if (!typingPeerIds.value.includes(uid)) typingPeerIds.value = [...typingPeerIds.value, uid]
  typingTimers[uid] = setTimeout(() => {
    delete typingTimers[uid]
    typingPeerIds.value = typingPeerIds.value.filter((x) => x !== uid)
  }, 4000)
}

function closeWs() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function sendComposerTyping(payload: { active: boolean }) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  ws.send(JSON.stringify({ type: 'typing', active: payload.active }))
}

function openWs(topicId: number) {
  closeWs()
  if (!auth.token) return
  ws = api.createCommunityTopicSocket(topicId, auth.token, (evt) => {
    if (evt.type === 'community_message' && evt.topic_id === topicId) {
      messages.value = [...messages.value, evt.message]
      selectedHeat.value = evt.heat_score || selectedHeat.value
      return
    }
    if (evt.type === 'typing' && evt.topic_id === topicId) {
      const selfId = auth.userId
      if (selfId != null && evt.user_id === selfId) return
      refreshTypingPeer(evt.user_id, evt.active)
    }
  })
}

async function fetchTopicsList() {
  const skillTag =
    typeof route.query.skill_tag === 'string' && route.query.skill_tag.trim()
      ? route.query.skill_tag.trim()
      : undefined
  const res = await api.fetchCommunityTopics({
    skill_tag: skillTag,
    q: query.value || undefined,
    limit: 40,
  })
  topics.value = res.data.items || []
}

function applyTaskDraftFromRoute() {
  const tq = route.query.task_id
  if (!tq || !canSpeak.value) return
  const id = Number(tq)
  if (!(id > 0)) return
  composerDraftNudge.value = {
    text: String(t('community.draftFromTask', { id: String(id) })),
    nonce: Date.now(),
  }
}

async function trySelectTopic(id: number): Promise<boolean> {
  try {
    await selectTopic(id)
    return true
  } catch {
    closeWs()
    selectedTopicId.value = null
    messages.value = []
    selectedHeat.value = 0
    return false
  }
}

async function bootstrapCommunityView() {
  if (!isCommunityRoutePath()) return
  clearTypingPeers()
  closeWs()
  await fetchTopicsList()
  const topicQ = route.query.topic_id
  if (topicQ) {
    const tid = Number(topicQ)
    if (tid > 0) {
      const ok = await trySelectTopic(tid)
      if (!ok && topics.value.length) await selectTopic(topics.value[0].id)
      applyTaskDraftFromRoute()
      return
    }
  }
  if (selectedTopicId.value != null) {
    const stillHere = topics.value.some((x) => x.id === selectedTopicId.value)
    if (!stillHere) {
      selectedTopicId.value = null
      messages.value = []
      selectedHeat.value = 0
    }
  }
  if (!selectedTopicId.value && topics.value.length) {
    await selectTopic(topics.value[0].id)
  } else if (selectedTopicId.value) {
    const ok = await trySelectTopic(selectedTopicId.value)
    if (!ok && topics.value.length) await selectTopic(topics.value[0].id)
  }
  applyTaskDraftFromRoute()
}

async function loadHot() {
  const res = await api.fetchCommunityHotFeed(10)
  hotFeed.value = res.data.items || []
}

async function selectTopic(id: number) {
  clearTypingPeers()
  selectedTopicId.value = id
  const res = await api.fetchCommunityMessages(id, { limit: 80 })
  messages.value = res.data.items || []
  selectedHeat.value = res.data.topic?.heat_score || 0
  openWs(id)
}

async function onSearch(q: string) {
  query.value = q
  await fetchTopicsList()
  if (topics.value.length && !topics.value.some((x) => x.id === selectedTopicId.value)) {
    await selectTopic(topics.value[0].id)
  }
}

async function sendMessage(payload: { content: string; attachments: api.CommunityAttachment[]; intent: string }) {
  if (!selectedTopicId.value) return
  postLoading.value = true
  try {
    await api.postCommunityMessage(selectedTopicId.value, {
      content: payload.content,
      attachments: payload.attachments,
      reply_to_id: replyToId.value || undefined,
      intent: payload.intent && payload.intent !== 'chat' ? payload.intent : undefined,
    })
    replyToId.value = null
    replyToSummary.value = ''
  } finally {
    postLoading.value = false
  }
}

function startReply(payload: { id: number; summary: string }) {
  replyToId.value = payload.id
  replyToSummary.value = payload.summary
}

function cancelReply() {
  replyToId.value = null
  replyToSummary.value = ''
}

function applyStarterDraft(text: string) {
  if (!canSpeak.value || !text.trim()) return
  composerDraftNudge.value = { text: text.trim(), nonce: Date.now() }
}

onMounted(async () => {
  try {
    if (!localStorage.getItem(COMMUNITY_ONBOARD_KEY)) showCommunityOnboarding.value = true
  } catch {
    showCommunityOnboarding.value = true
  }
  canSpeak.value = false
  if (auth.isLoggedIn) {
    try {
      const me = await api.fetchMyAgents()
      canSpeak.value = (me.data.agents || []).length > 0
      allAgents.value = (me.data.agents || []).map((x: any) => ({ id: Number(x.id), name: String(x.name || `Agent-${x.id}`) }))
    } catch {
      canSpeak.value = false
    }
    try {
      const sk = await api.fetchSkills({ verified_only: true, limit: 80, sort: 'tasks_desc' })
      skills.value = sk.data.items || []
    } catch {
      skills.value = []
    }
  }
  await loadHot()
  await bootstrapCommunityView()
})

watch(
  () => ({
    skill_tag: route.query.skill_tag,
    topic_id: route.query.topic_id,
    task_id: route.query.task_id,
    path: route.path,
  }),
  async (_curr, prev) => {
    if (!prev) return
    if (!isCommunityRoutePath()) return
    await bootstrapCommunityView()
  },
)

watch(canSpeak, (v) => {
  if (v && isCommunityRoutePath()) applyTaskDraftFromRoute()
})

onBeforeUnmount(() => {
  clearTypingPeers()
  closeWs()
})

async function pushSkill() {
  if (!selectedTopicId.value || !pushTargetAgentId.value || !pushSkillId.value) return
  pushLoading.value = true
  try {
    await api.pushCommunitySkill(selectedTopicId.value, {
      target_agent_id: pushTargetAgentId.value,
      skill_id: pushSkillId.value,
      note: pushNote.value.trim() || undefined,
    })
    pushNote.value = ''
  } finally {
    pushLoading.value = false
  }
}
</script>

<style scoped>
.community-view { max-width: 1320px; margin: 0 auto; padding: 0 16px; }
.community-header h1 { margin: 0 0 6px; }
.community-header p { margin: 0 0 14px; opacity: .8; }
.growth-strip { margin: 0 0 14px !important; font-size: 13px; opacity: .88 !important; line-height: 1.5; }
.growth-link { color: #a78bfa; text-decoration: none; }
.growth-link:hover { text-decoration: underline; }
.community-layout { display:grid; grid-template-columns: 280px 1fr 280px; gap:12px; align-items:start; }
.community-main { display:flex; flex-direction:column; gap:10px; }
.typing-hint { margin:0; font-size:12px; opacity:.72; min-height:18px; color:#a78bfa; }
.community-right { display:flex; flex-direction:column; gap:10px; }
.skill-push-panel { border:1px solid var(--border-color, #2a2a2a); border-radius:12px; padding:10px; display:flex; flex-direction:column; gap:8px; }
.skill-push-panel h4 { margin:0; font-size:14px; }
.hint { margin:0; font-size:12px; opacity:.75; }
.push-btn { width:100%; }
@media (max-width: 1100px) { .community-layout { grid-template-columns: 1fr; } }
.comm-onboard-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10050;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.comm-onboard-card {
  max-width: 420px;
  width: 100%;
  border-radius: 14px;
  padding: 20px;
  background: var(--card-bg, #1a1a1e);
  border: 1px solid rgba(167, 139, 250, 0.35);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
}
.comm-onboard-card h3 { margin: 0 0 12px; font-size: 17px; }
.comm-onboard-steps { margin: 0 0 16px; padding-left: 18px; line-height: 1.55; font-size: 14px; opacity: 0.92; }
.comm-onboard-steps li { margin-bottom: 8px; }
.comm-onboard-btn {
  width: 100%;
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: #4f46e5;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.comm-onboard-btn:hover { filter: brightness(1.06); }
.composer-upsell {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(167, 139, 250, 0.28);
  background: rgba(79, 70, 229, 0.07);
  font-size: 13px;
  line-height: 1.5;
}
.composer-upsell__lead { margin: 0 0 8px; }
.composer-upsell__links { margin: 0; font-size: 13px; }
.composer-upsell--need-agent > p:first-child { margin: 0 0 10px; }
.composer-upsell__sep { margin: 0 8px; opacity: .55; }
.composer-upsell__nav-hint { opacity: .75; font-size: 12px; }
.composer-upsell__actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.composer-upsell__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  background: #4f46e5;
  color: #fff;
}
.composer-upsell__btn--ghost {
  background: transparent;
  color: #c4b5fd;
  border: 1px solid rgba(196, 181, 253, 0.45);
}
.composer-upsell__btn:hover { filter: brightness(1.05); }
.composer-upsell__muted { margin: 0; font-size: 12px; opacity: .72; }
</style>
