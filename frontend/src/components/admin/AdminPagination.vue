<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '../ui/button'
import { safeT } from '../../i18n'

defineProps<{
  loading?: boolean
  from: number
  to: number
  total: number
  hasPrev: boolean
  hasNext: boolean
}>()

const emit = defineEmits<{ prev: []; next: [] }>()

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
</script>

<template>
  <div v-if="total > 0" class="admin-pagination">
    <Button
      size="sm"
      variant="secondary"
      type="button"
      :disabled="!hasPrev || loading"
      @click="emit('prev')"
    >
      {{ t('admin.prev') || '上一页' }}
    </Button>
    <span class="admin-page-meta">{{ from }}–{{ to }} / {{ total }}</span>
    <Button
      size="sm"
      variant="secondary"
      type="button"
      :disabled="!hasNext || loading"
      @click="emit('next')"
    >
      {{ t('admin.next') || '下一页' }}
    </Button>
  </div>
</template>
