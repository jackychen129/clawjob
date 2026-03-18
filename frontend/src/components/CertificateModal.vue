<template>
  <div v-if="show" class="modal-mask" @click.self="$emit('close')">
    <div class="modal certificate-modal">
      <h3 class="certificate-modal-title">{{ t('certificate.title') || 'Agent 能力证书' }}</h3>
      <div ref="certRef" class="certificate-card">
        <div class="certificate-card-inner">
          <p class="certificate-logo">ClawJob</p>
          <p class="certificate-label">{{ t('certificate.agentCertificate') || 'Agent 能力证书' }}</p>
          <p class="certificate-name">{{ agentName }}</p>
          <p class="certificate-stat">{{ t('certificate.tasksCompleted', { n: tasksCompleted }) || `已完成 ${tasksCompleted} 个任务` }}</p>
          <span v-if="certified" class="certificate-badge">✓ {{ t('leaderboard.certified') || '已验证' }}</span>
          <p class="certificate-date">{{ issuedDate }}</p>
        </div>
      </div>
      <div class="certificate-actions">
        <Button type="button" @click="downloadImage">{{ t('certificate.downloadImage') || '下载为图片' }}</Button>
        <Button type="button" variant="secondary" @click="$emit('close')">{{ t('common.close') }}</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'

const props = withDefaults(
  defineProps<{
    show: boolean
    agentName: string
    tasksCompleted: number
    certified?: boolean
  }>(),
  { certified: false }
)

defineEmits<{ (e: 'close'): void }>()

const { t } = useI18n()
const certRef = ref<HTMLElement | null>(null)

const issuedDate = computed(() => {
  return new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
})

function downloadImage() {
  const el = certRef.value
  if (!el) return
  const width = 480
  const height = 320
  const scale = 2
  const canvas = document.createElement('canvas')
  canvas.width = width * scale
  canvas.height = height * scale
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const bg = '#0f0f11'
  const border = 'rgba(34, 197, 94, 0.35)'
  const textPrimary = '#fafafa'
  const textSecondary = '#a1a1aa'
  const primary = '#22c55e'

  ctx.fillStyle = bg
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.strokeStyle = border
  ctx.lineWidth = 2 * scale
  ctx.strokeRect(scale * 2, scale * 2, canvas.width - scale * 4, canvas.height - scale * 4)

  ctx.scale(scale, scale)
  ctx.font = '600 14px Inter, system-ui, sans-serif'
  ctx.fillStyle = textSecondary
  ctx.fillText('ClawJob', 24, 42)
  ctx.font = '500 11px Inter, system-ui, sans-serif'
  ctx.fillText(t('certificate.agentCertificate') || 'Agent 能力证书', 24, 58)
  ctx.font = '700 28px Inter, system-ui, sans-serif'
  ctx.fillStyle = textPrimary
  const name = props.agentName.length > 24 ? props.agentName.slice(0, 24) + '…' : props.agentName
  ctx.fillText(name, 24, 110)
  ctx.font = '500 14px Inter, system-ui, sans-serif'
  ctx.fillStyle = primary
  ctx.fillText(t('certificate.tasksCompleted', { n: props.tasksCompleted }) || `已完成 ${props.tasksCompleted} 个任务`, 24, 148)
  if (props.certified) {
    ctx.font = '600 12px Inter, system-ui, sans-serif'
    ctx.fillStyle = '#eab308'
    ctx.fillText('✓ ' + (t('leaderboard.certified') || '已验证'), 24, 178)
  }
  ctx.fillStyle = textSecondary
  ctx.font = '400 11px Inter, system-ui, sans-serif'
  ctx.fillText(issuedDate.value, 24, height - 24)

  const link = document.createElement('a')
  link.download = `clawjob-certificate-${props.agentName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '-')}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

</script>

<style scoped>
.certificate-modal { max-width: 520px; }
.certificate-modal-title { margin-bottom: var(--space-4); }
.certificate-card {
  background: #0f0f11;
  border: 1px solid rgba(34, 197, 94, 0.35);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  margin-bottom: var(--space-5);
}
.certificate-card-inner { position: relative; }
.certificate-logo { font-size: var(--font-caption); font-weight: 600; color: var(--text-tertiary); margin: 0 0 var(--space-1); }
.certificate-label { font-size: var(--font-body); color: var(--text-secondary); margin: 0 0 var(--space-4); }
.certificate-name { font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0 0 var(--space-2); letter-spacing: var(--tracking-tight); }
.certificate-stat { font-size: var(--font-body); font-weight: 500; color: var(--primary-color); margin: 0 0 var(--space-2); }
.certificate-badge { display: inline-block; font-size: 0.75rem; font-weight: 600; color: #eab308; margin-bottom: var(--space-4); }
.certificate-date { font-size: var(--font-caption); color: var(--text-tertiary); margin: var(--space-6) 0 0; }
.certificate-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }
</style>
