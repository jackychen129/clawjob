<script setup lang="ts">
defineProps<{
  loading?: boolean
  skeletonCount?: number
}>()
</script>

<template>
  <div v-if="loading" class="admin-metrics-v2">
    <div v-for="i in skeletonCount ?? 4" :key="i" class="admin-metric-skeleton">
      <div class="tw-skeleton admin-log-skel-row" />
      <div class="tw-skeleton admin-log-skel-row" style="height: 1.75rem; margin-top: 0.5rem" />
    </div>
  </div>
  <div v-else class="admin-metrics-v2 motion-stagger">
    <slot />
  </div>
</template>
