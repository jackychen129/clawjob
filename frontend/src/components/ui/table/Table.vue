<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '../../../lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div class="ui-table-wrap w-full overflow-x-auto">
    <table
      :class="
        cn(
          'ui-table w-full caption-bottom border-collapse text-sm',
          props.class,
        )
      "
    >
      <slot />
    </table>
  </div>
</template>

<style scoped>
.ui-table-wrap {
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-layer-1);
}
.ui-table :deep(thead) {
  border-bottom: var(--border-hairline);
  background: var(--surface-2);
}
.ui-table :deep(th) {
  font-size: var(--font-caption);
  font-weight: 600;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-secondary);
}
.ui-table :deep(tbody tr) {
  border-bottom: var(--border-hairline);
  transition: background-color var(--duration-fast) var(--ease-apple);
}
@media (prefers-reduced-motion: reduce) {
  .ui-table :deep(tbody tr) {
    transition: none;
  }
}
.ui-table :deep(tbody tr:last-child) {
  border-bottom: none;
}
.ui-table :deep(tbody tr:hover) {
  background: var(--card-hover);
}
.ui-table :deep(td) {
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
</style>
