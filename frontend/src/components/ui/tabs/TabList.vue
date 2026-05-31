<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '../../../lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div
    role="tablist"
    :class="
      cn(
        'ui-tab-list inline-flex h-10 items-center gap-1 rounded-lg border border-[var(--border-muted-strong)] bg-[var(--surface-2)] p-1',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
