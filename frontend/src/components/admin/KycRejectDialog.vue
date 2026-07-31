<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'

const props = defineProps<{
  open: boolean
  kycId: number | null
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  confirm: [payload: { kycId: number; reason: string }]
}>()

const { t } = useI18n()
const reason = ref(t('admin.kycRejectDefault') || '资料不完整')

watch(() => props.open, (v) => {
  if (v) reason.value = t('admin.kycRejectDefault') || '资料不完整'
})

function onOpenChange(v: boolean) {
  emit('update:open', v)
}

function confirm() {
  if (!props.kycId) return
  emit('confirm', { kycId: props.kycId, reason: reason.value.trim() || '资料不完整' })
}
</script>

<template>
  <Dialog
    :open="open"
    :title="t('admin.kycReject') || '驳回 KYC'"
    :description="kycId ? `ID #${kycId}` : undefined"
    @update:open="onOpenChange"
  >
    <div class="admin-form-dialog__field">
      <label class="admin-form-dialog__label" for="kyc-reject-reason">
        {{ t('admin.kycRejectReason') || '驳回原因' }}
      </label>
      <Input id="kyc-reject-reason" v-model="reason" />
    </div>
    <div class="admin-dispute-actions" style="margin-top: 1rem; justify-content: flex-end">
      <Button type="button" variant="secondary" :disabled="loading" @click="onOpenChange(false)">
        {{ t('common.cancel') || '取消' }}
      </Button>
      <Button type="button" variant="secondary" :disabled="loading || !kycId" @click="confirm">
        {{ loading ? '…' : (t('admin.kycReject') || '驳回') }}
      </Button>
    </div>
  </Dialog>
</template>
