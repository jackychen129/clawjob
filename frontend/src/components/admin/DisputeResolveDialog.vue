<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog } from '../ui/dialog'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

const props = defineProps<{
  open: boolean
  taskId: number | null
  taskTitle?: string
  resolutionType: 'resume' | 'force_confirm' | null
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: [payload: { taskId: number; resolutionType: 'resume' | 'force_confirm'; note: string }]
}>()

const { t } = useI18n()
const note = ref('')

function onOpenChange(v: boolean) {
  if (!v) note.value = ''
  emit('update:open', v)
}

function confirm() {
  if (!props.taskId || !props.resolutionType) return
  emit('confirm', {
    taskId: props.taskId,
    resolutionType: props.resolutionType,
    note: note.value.trim(),
  })
}

const title = () => {
  if (props.resolutionType === 'force_confirm') {
    return t('admin.disputeDialogForceTitle') || '强制验收'
  }
  return t('admin.disputeDialogResumeTitle') || '恢复执行'
}
</script>

<template>
  <Dialog
    :open="open"
    :title="title()"
    :description="taskTitle ? `#${taskId} ${taskTitle}` : undefined"
    @update:open="onOpenChange"
  >
    <div class="admin-form-dialog__field">
      <label class="admin-form-dialog__label" for="dispute-note">
        {{ t('admin.disputeDialogNote') || '处理备注（可选）' }}
      </label>
      <Textarea
        id="dispute-note"
        v-model="note"
        rows="3"
        :placeholder="t('admin.disputeDialogNotePlaceholder') || '记录裁决依据，便于审计追溯'"
      />
    </div>
    <div class="admin-dispute-actions" style="margin-top: 1rem; justify-content: flex-end">
      <Button type="button" variant="secondary" :disabled="loading" @click="onOpenChange(false)">
        {{ t('common.cancel') || '取消' }}
      </Button>
      <Button type="button" :disabled="loading || !taskId" @click="confirm">
        {{ loading ? '…' : (t('common.confirm') || '确认') }}
      </Button>
    </div>
  </Dialog>
</template>
