<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { safeT } from '../../i18n'
import { ADMIN_ROUTE_LABELS } from '../../composables/admin/useAdminNav'

const route = useRoute()
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const currentLabel = computed(() => {
  const key = route.name ? ADMIN_ROUTE_LABELS[String(route.name)] : null
  return key ? t(key) : t('admin.title')
})
</script>

<template>
  <nav class="admin-breadcrumb" aria-label="Breadcrumb">
    <span class="admin-breadcrumb__root">{{ t('admin.title') || '管理后台' }}</span>
    <ChevronRight :size="14" class="admin-breadcrumb__sep" aria-hidden="true" />
    <span class="admin-breadcrumb__current" aria-current="page">{{ currentLabel }}</span>
  </nav>
</template>
