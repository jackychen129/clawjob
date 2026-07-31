<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Dialog } from '../ui/dialog'
import { Button } from '../ui/button'

defineProps<{
  open: boolean
  host: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: []
}>()

const { t } = useI18n()
</script>

<template>
  <Dialog
    :open="open"
    :title="t('admin.circuitOpen') || '强制打开熔断'"
    :description="host ? `Host: ${host}` : undefined"
    @update:open="emit('update:open', $event)"
  >
    <p class="hint" style="margin: 0">
      {{ t('admin.circuitOpenConfirm') || '确认强制打开熔断？下游请求将被阻断。' }}
    </p>
    <div class="admin-dispute-actions" style="margin-top: 1rem; justify-content: flex-end">
      <Button type="button" variant="secondary" :disabled="loading" @click="emit('update:open', false)">
        {{ t('common.cancel') || '取消' }}
      </Button>
      <Button type="button" :disabled="loading" @click="emit('confirm')">
        {{ loading ? '…' : (t('common.confirm') || '确认') }}
      </Button>
    </div>
  </Dialog>
</template>
