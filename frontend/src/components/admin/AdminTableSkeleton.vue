<script setup lang="ts">
defineProps<{
  rows?: number
}>()
</script>

<template>
  <div class="admin-table-skeleton" aria-busy="true" aria-label="Loading">
    <div v-for="i in rows ?? 5" :key="i" class="tw-skeleton admin-table-skeleton__row" />
  </div>
</template>
