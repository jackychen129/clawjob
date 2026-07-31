<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

defineProps<{
  message: string
}>()
</script>

<template>
  <div class="admin-empty-state" role="status">
    <Inbox :size="32" class="admin-empty-state__icon" aria-hidden="true" />
    <p class="admin-empty-state__text">{{ message }}</p>
  </div>
</template>
