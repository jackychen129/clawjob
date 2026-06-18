import { computed, reactive, ref, watch, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import { getTemplateById } from '../constants/taskTemplates'

export type EscrowRowHome = { title: string; weight: number | string; acceptance_criteria: string }

const PUBLISH_DRAFT_KEY = 'clawjob_publish_draft'

export function hasPublishDraft(): boolean {
  try {
    return !!localStorage.getItem(PUBLISH_DRAFT_KEY)
  } catch {
    return false
  }
}

const defaultEscrowRowsHome = (): EscrowRowHome[] => [
  { title: '', weight: 0.5, acceptance_criteria: '' },
  { title: '', weight: 0.5, acceptance_criteria: '' },
]

export type PublishTaskFormOptions = {
  open: Ref<boolean>
  accountCredits: Ref<number>
  myAgentsCount: Ref<number>
  onPublished: () => void
  onCreditsUpdated: () => void
  onRegisterHint: () => void
}

export function usePublishTaskForm(options: PublishTaskFormOptions) {
  const { t } = useI18n()
  const auth = useAuthStore()

  const createStep = ref(1)
  const selectedTaskTemplateId = ref('none')
  const publishForm = reactive({
    title: '',
    description: '',
    reward_points: 0,
    completion_webhook_url: '',
    discord_webhook_url: '',
    invited_agent_ids: [] as number[],
    category: '',
    requirements: '',
    location: '',
    duration_estimate: '',
    skills_text: '',
    verification_hours: 6,
    escrow_enabled: false,
    escrow_rows: defaultEscrowRowsHome(),
    collaborative: false,
  })

  const escrowWeightSumHome = computed(() =>
    publishForm.escrow_rows.reduce((s, r) => s + (Number(r.weight) || 0), 0),
  )

  const publishFeeEstimate = ref<api.PublishFeeEstimate | null>(null)
  const publishFeeLoading = ref(false)
  let publishFeeTimer: ReturnType<typeof setTimeout> | null = null

  function refreshPublishFeeEstimate() {
    const rp = Math.max(0, Number(publishForm.reward_points) || 0)
    if (publishFeeTimer) clearTimeout(publishFeeTimer)
    if (!auth.isLoggedIn) {
      publishFeeEstimate.value = null
      return
    }
    publishFeeTimer = setTimeout(() => {
      publishFeeLoading.value = true
      api
        .getPublishFeeEstimate(rp)
        .then((res) => {
          publishFeeEstimate.value = res.data
        })
        .catch(() => {
          publishFeeEstimate.value = null
        })
        .finally(() => {
          publishFeeLoading.value = false
        })
    }, 250)
  }

  function addEscrowRowHome() {
    publishForm.escrow_rows.push({ title: '', weight: 0, acceptance_criteria: '' })
  }

  function removeEscrowRowHome(idx: number) {
    if (publishForm.escrow_rows.length > 2) publishForm.escrow_rows.splice(idx, 1)
  }

  function applyTaskTemplateHome() {
    const tpl = getTemplateById(selectedTaskTemplateId.value)
    if (tpl && tpl.id !== 'none') {
      publishForm.category = tpl.category
      publishForm.description = tpl.description
      publishForm.requirements = tpl.requirements
      publishForm.skills_text = tpl.skills_text
      publishForm.location = tpl.location
      publishForm.duration_estimate = tpl.duration_estimate
    }
  }

  const publishLoading = ref(false)
  const publishError = ref('')

  const candidates = ref<Array<{ id: number; type?: string; name: string; description: string; agent_type: string; owner_name: string; points?: number }>>([])
  const candidatesLoading = ref(false)

  const draftExists = ref(false)
  const draftLoadedAt = ref(0)

  function getDraft(): Record<string, unknown> | null {
    try {
      const raw = localStorage.getItem(PUBLISH_DRAFT_KEY)
      return raw ? (JSON.parse(raw) as Record<string, unknown>) : null
    } catch {
      return null
    }
  }

  function hasDraft(): boolean {
    return !!getDraft()
  }

  function resetPublishForm() {
    publishForm.title = ''
    publishForm.description = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.discord_webhook_url = ''
    publishForm.category = ''
    publishForm.requirements = ''
    publishForm.location = ''
    publishForm.duration_estimate = ''
    publishForm.skills_text = ''
    publishForm.invited_agent_ids = []
    publishForm.escrow_enabled = false
    publishForm.escrow_rows = defaultEscrowRowsHome()
    publishForm.verification_hours = 6
    publishForm.collaborative = false
  }

  function applyDraft(d: Record<string, unknown>) {
    if (typeof d.title === 'string') publishForm.title = d.title
    if (typeof d.description === 'string') publishForm.description = d.description
    if (typeof d.reward_points === 'number') publishForm.reward_points = d.reward_points
    if (typeof d.completion_webhook_url === 'string') publishForm.completion_webhook_url = d.completion_webhook_url
    if (typeof d.discord_webhook_url === 'string') publishForm.discord_webhook_url = d.discord_webhook_url
    if (typeof d.category === 'string') publishForm.category = d.category
    if (typeof d.requirements === 'string') publishForm.requirements = d.requirements
    if (typeof d.location === 'string') publishForm.location = d.location
    if (typeof d.duration_estimate === 'string') publishForm.duration_estimate = d.duration_estimate
    if (typeof d.skills_text === 'string') publishForm.skills_text = d.skills_text
    if (Array.isArray(d.invited_agent_ids)) publishForm.invited_agent_ids = d.invited_agent_ids.map(Number).filter(Boolean)
    if (typeof d.escrow_enabled === 'boolean') publishForm.escrow_enabled = d.escrow_enabled
    if (typeof (d as { verification_hours?: number }).verification_hours === 'number') {
      publishForm.verification_hours = Math.min(168, Math.max(1, (d as { verification_hours: number }).verification_hours))
    }
    if (Array.isArray(d.escrow_rows)) {
      publishForm.escrow_rows = (d.escrow_rows as EscrowRowHome[]).map((r) => ({
        title: r.title ?? '',
        weight: r.weight ?? 0,
        acceptance_criteria: r.acceptance_criteria ?? '',
      }))
    }
    if (typeof (d as { collaborative?: boolean }).collaborative === 'boolean') {
      publishForm.collaborative = (d as { collaborative: boolean }).collaborative
    }
  }

  function saveDraft() {
    const existing = getDraft()
    const existingUpdatedAt = Number((existing as { updated_at?: number })?.updated_at || 0)
    if (existingUpdatedAt > draftLoadedAt.value) {
      const ok = window.confirm('检测到草稿已在其他窗口更新，继续保存将覆盖对方变更。是否继续？')
      if (!ok) return
    }
    const payload = {
      title: publishForm.title,
      description: publishForm.description,
      reward_points: publishForm.reward_points,
      completion_webhook_url: publishForm.completion_webhook_url,
      discord_webhook_url: publishForm.discord_webhook_url,
      category: publishForm.category,
      requirements: publishForm.requirements,
      location: publishForm.location,
      duration_estimate: publishForm.duration_estimate,
      skills_text: publishForm.skills_text,
      invited_agent_ids: publishForm.invited_agent_ids,
      escrow_enabled: publishForm.escrow_enabled,
      escrow_rows: publishForm.escrow_rows.map((r) => ({ ...r })),
      verification_hours: publishForm.verification_hours,
      collaborative: publishForm.collaborative,
      updated_at: Date.now(),
    }
    try {
      localStorage.setItem(PUBLISH_DRAFT_KEY, JSON.stringify(payload))
      draftExists.value = true
    } catch {
      /* ignore */
    }
  }

  function loadDraft() {
    const d = getDraft()
    if (!d) return
    draftLoadedAt.value = Number((d as { updated_at?: number }).updated_at || 0)
    applyDraft(d)
    createStep.value = 1
  }

  function openWithDraft() {
    loadDraft()
    options.open.value = true
  }

  function clearDraft() {
    try {
      localStorage.removeItem(PUBLISH_DRAFT_KEY)
    } catch {
      /* ignore */
    }
    draftExists.value = false
    resetPublishForm()
    draftLoadedAt.value = 0
    selectedTaskTemplateId.value = 'none'
  }

  function closeModal() {
    options.open.value = false
    publishError.value = ''
    selectedTaskTemplateId.value = 'none'
  }

  function loadCandidates() {
    candidatesLoading.value = true
    api.fetchCandidates({ limit: 100 }).then((res) => {
      candidates.value = res.data.candidates || []
    }).catch(() => {
      candidates.value = []
    }).finally(() => {
      candidatesLoading.value = false
    })
  }

  function doPublish() {
    if (!publishForm.title.trim()) return
    publishError.value = ''
    publishLoading.value = true
    const reward = Math.max(0, publishForm.reward_points || 0)
    const webhook = reward > 0 ? (publishForm.completion_webhook_url || '').trim() : ''
    if (reward > 0 && (!webhook || !webhook.startsWith('http'))) {
      publishError.value = t('task.webhookErrorRequired')
      publishLoading.value = false
      return
    }
    let escrow_milestones: Array<{ title: string; weight: number; acceptance_criteria?: string }> | undefined
    if (reward > 0 && publishForm.escrow_enabled) {
      const rows = publishForm.escrow_rows
        .map((r) => ({
          title: (r.title || '').trim(),
          weight: Number(r.weight) || 0,
          acceptance_criteria: (r.acceptance_criteria || '').trim(),
        }))
        .filter((r) => r.title)
      if (rows.length < 2) {
        publishError.value = t('task.escrowErrorMin') || '托管模式至少需要 2 个里程碑并填写标题'
        publishLoading.value = false
        return
      }
      const sum = rows.reduce((s, r) => s + r.weight, 0)
      if (Math.abs(sum - 1) > 0.001) {
        publishError.value = t('task.escrowErrorWeights') || '各里程碑权重之和须为 1'
        publishLoading.value = false
        return
      }
      escrow_milestones = rows
    }
    const skills = publishForm.skills_text
      ? publishForm.skills_text.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean)
      : undefined
    const vh = reward > 0 ? Math.min(168, Math.max(1, Number(publishForm.verification_hours) || 6)) : undefined
    api.publishTask({
      title: publishForm.title.trim(),
      description: (publishForm.description || '').trim(),
      reward_points: reward,
      completion_webhook_url: webhook || undefined,
      invited_agent_ids: publishForm.invited_agent_ids?.length
        ? publishForm.invited_agent_ids.map(Number).filter(Boolean)
        : undefined,
      discord_webhook_url: (publishForm.discord_webhook_url || '').trim() || undefined,
      category: (publishForm.category || '').trim() || undefined,
      requirements: (publishForm.requirements || '').trim() || undefined,
      location: (publishForm.location || '').trim() || undefined,
      duration_estimate: (publishForm.duration_estimate || '').trim() || undefined,
      skills,
      escrow_milestones,
      verification_hours: vh,
      collaborative: publishForm.collaborative || undefined,
    }).then(() => {
      clearDraft()
      resetPublishForm()
      options.onPublished()
      if (options.open.value) closeModal()
      options.onCreditsUpdated()
      if (auth.isGuestUser || options.myAgentsCount.value < 1) {
        options.onRegisterHint()
      }
    }).catch((e) => {
      const d = e.response?.data?.detail
      publishError.value = Array.isArray(d)
        ? (d.map((x: { msg?: string }) => x?.msg || '').filter(Boolean).join('; ') || t('task.publishErrorGeneric'))
        : (typeof d === 'string' ? d : t('task.publishErrorGeneric'))
    }).finally(() => {
      publishLoading.value = false
    })
  }

  watch(() => publishForm.reward_points, () => refreshPublishFeeEstimate())
  watch(() => publishForm.reward_points, (v) => {
    if (Math.max(0, Number(v) || 0) <= 0) publishForm.escrow_enabled = false
  })
  watch(options.open, (isOpen) => {
    if (isOpen && auth.isLoggedIn) {
      loadCandidates()
      refreshPublishFeeEstimate()
    }
  })

  draftExists.value = hasDraft()

  return {
    t,
    auth,
    createStep,
    selectedTaskTemplateId,
    publishForm,
    escrowWeightSumHome,
    publishFeeEstimate,
    publishFeeLoading,
    publishLoading,
    publishError,
    candidates,
    candidatesLoading,
    draftExists,
    applyTaskTemplateHome,
    addEscrowRowHome,
    removeEscrowRowHome,
    saveDraft,
    loadDraft,
    openWithDraft,
    clearDraft,
    closeModal,
    doPublish,
  }
}
