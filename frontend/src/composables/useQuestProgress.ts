import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'

export type QuestStepId = 'join' | 'quest' | 'paid' | 'settle'

const STORAGE_KEY = 'clawjob_quest_progress_v1'

type StoredProgress = {
  dismissed?: boolean
  registeredAt?: string
  questDoneHint?: boolean
  paidTakenHint?: boolean
}

function readStore(): StoredProgress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as StoredProgress) : {}
  } catch {
    return {}
  }
}

function writeStore(patch: Partial<StoredProgress>) {
  try {
    const next = { ...readStore(), ...patch }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    return next
  } catch {
    return { ...readStore(), ...patch }
  }
}

function isGrowthPath(path: string) {
  return path === '/join' || path.startsWith('/r/') || path === '/tasks' || path === '/account'
}

/**
 * Cross-page earn path: Join → onboarding quests → paid agent_direct → settlement.
 * Active step is primarily route-driven; localStorage + mine tasks refine completion hints.
 */
export function useQuestProgress() {
  const route = useRoute()
  const auth = useAuthStore()
  const store = ref<StoredProgress>(readStore())

  const steps: Array<{ id: QuestStepId; labelKey: string; to: string }> = [
    { id: 'join', labelKey: 'questProgress.stepJoin', to: '/join' },
    { id: 'quest', labelKey: 'questProgress.stepQuest', to: '/tasks?onboarding=1' },
    { id: 'paid', labelKey: 'questProgress.stepPaid', to: '/tasks?sort=reward&settlement=agent_direct' },
    { id: 'settle', labelKey: 'questProgress.stepSettle', to: '/account' },
  ]

  const activeId = computed<QuestStepId>(() => {
    const path = route.path
    const q = route.query
    if (path === '/join' || path.startsWith('/r/')) return 'join'
    if (path === '/tasks' && String(q.onboarding ?? '') === '1') return 'quest'
    if (path === '/account') return 'settle'
    if (path === '/tasks') return 'paid'
    if (auth.isLoggedIn && store.value.paidTakenHint) return 'settle'
    if (auth.isLoggedIn && store.value.questDoneHint) return 'paid'
    if (auth.isLoggedIn) return 'quest'
    return 'join'
  })

  const activeIndex = computed(() => {
    const idx = steps.findIndex((s) => s.id === activeId.value)
    return idx >= 0 ? idx : 0
  })

  const visible = computed(() => {
    if (store.value.dismissed) return false
    if (route.meta.layout === 'marketing') return false
    return isGrowthPath(route.path) || String(route.query.onboarding ?? '') === '1'
  })

  function dismiss() {
    store.value = writeStore({ dismissed: true })
  }

  function markRegistered() {
    store.value = writeStore({ registeredAt: new Date().toISOString() })
  }

  async function refreshSignals() {
    if (!auth.isLoggedIn) return
    try {
      const res = await api.fetchMyAcceptedTasks({ limit: 50 })
      const list = res.data?.tasks || []
      const questDone = list.some(
        (t) =>
          String(t.title || '').includes('【新手 Quest') &&
          (t.status === 'completed' || t.status === 'pending_verification'),
      )
      const paid = list.some((t) => Number(t.reward_points || 0) > 0)
      if (questDone) store.value = writeStore({ questDoneHint: true })
      if (paid) store.value = writeStore({ paidTakenHint: true })
    } catch {
      /* route-only progress still works */
    }
  }

  watch(
    () => [auth.isLoggedIn, route.fullPath] as const,
    () => {
      store.value = readStore()
      if (auth.isLoggedIn && !store.value.registeredAt) markRegistered()
      void refreshSignals()
    },
    { immediate: true },
  )

  return {
    steps,
    activeId,
    activeIndex,
    visible,
    dismiss,
    markRegistered,
    refreshSignals,
  }
}
