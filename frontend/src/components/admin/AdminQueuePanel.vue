<script setup lang="ts">
/**
 * Shared admin queue panel: Card + title row + default slot + optional pagination footer.
 */
import { useI18n } from 'vue-i18n'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import AdminPagination from './AdminPagination.vue'
import { safeT } from '../../i18n'

defineProps<{
  title: string
  hint?: string
  loading?: boolean
  showRefresh?: boolean
  pageFrom?: number
  pageTo?: number
  pageTotal?: number
  pageHasPrev?: boolean
  pageHasNext?: boolean
}>()

const emit = defineEmits<{ refresh: []; prev: []; next: [] }>()

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
</script>

<template>
  <Card class="admin-panel">
    <CardHeader>
      <div class="admin-panel__head">
        <div>
          <CardTitle>{{ title }}</CardTitle>
          <CardDescription v-if="hint">{{ hint }}</CardDescription>
        </div>
        <Button
          v-if="showRefresh !== false"
          size="sm"
          variant="secondary"
          type="button"
          :disabled="loading"
          @click="emit('refresh')"
        >
          {{ t('common.retry') || '刷新' }}
        </Button>
      </div>
    </CardHeader>
    <CardContent class="pt-0">
      <slot />
      <AdminPagination
        v-if="pageTotal != null && pageTotal > 0"
        :loading="loading"
        :from="pageFrom ?? 0"
        :to="pageTo ?? 0"
        :total="pageTotal ?? 0"
        :has-prev="pageHasPrev ?? false"
        :has-next="pageHasNext ?? false"
        @prev="emit('prev')"
        @next="emit('next')"
      />
    </CardContent>
  </Card>
</template>
