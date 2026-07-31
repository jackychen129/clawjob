<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '../ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Table } from '../ui/table'
import AdminEmptyState from './AdminEmptyState.vue'
import AdminPagination from './AdminPagination.vue'
import AdminTableSkeleton from './AdminTableSkeleton.vue'
import { safeT } from '../../i18n'

defineProps<{
  title?: string
  hint?: string
  loading?: boolean
  isEmpty?: boolean
  emptyMessage?: string
  skeletonRows?: number
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
    <CardHeader v-if="title || $slots.header || $slots.actions || showRefresh !== false" class="pb-4">
      <div class="admin-panel__head">
        <div class="min-w-0">
          <slot name="header">
            <CardTitle v-if="title" class="text-lg">{{ title }}</CardTitle>
            <CardDescription v-if="hint">{{ hint }}</CardDescription>
          </slot>
        </div>
        <div class="admin-panel__actions">
          <slot name="actions" />
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
      </div>
    </CardHeader>
    <CardContent class="pt-0">
      <AdminTableSkeleton v-if="loading && isEmpty" :rows="skeletonRows" />
      <template v-else-if="!isEmpty">
        <Table>
          <thead>
            <slot name="head" />
          </thead>
          <tbody>
            <slot />
          </tbody>
        </Table>
      </template>
      <AdminEmptyState v-else :message="emptyMessage || t('common.noData') || '暂无数据'" />
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
