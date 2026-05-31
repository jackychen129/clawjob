<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, inject } from 'vue'
import { cn } from '../../../lib/utils'
import { tabsContextKey } from './tabs-context'

const props = defineProps<{
  value: string
  disabled?: boolean
  class?: HTMLAttributes['class']
}>()

const ctx = inject(tabsContextKey)
if (!ctx) throw new Error('Tab must be used within Tabs')

const selected = computed(() => ctx.modelValue.value === props.value)
const tabId = computed(() => `${ctx.baseId}-tab-${props.value}`)
const panelId = computed(() => `${ctx.baseId}-panel-${props.value}`)

function activate() {
  if (props.disabled) return
  ctx.setValue(props.value)
}
</script>

<template>
  <button
    :id="tabId"
    type="button"
    role="tab"
    :aria-selected="selected"
    :aria-controls="panelId"
    :tabindex="selected ? 0 : -1"
    :disabled="disabled"
    :class="
      cn(
        'ui-tab relative inline-flex h-8 items-center justify-center rounded-md px-3 text-sm font-medium text-[var(--text-secondary)] transition-colors duration-[var(--duration-fast)] motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
        selected &&
          'bg-[var(--surface-1)] text-[var(--text-primary)] shadow-[var(--shadow-layer-1)]',
        props.class,
      )
    "
    @click="activate"
  >
    <slot />
    <span
      v-if="selected"
      class="ui-tab-indicator absolute inset-x-2 -bottom-1 h-0.5 rounded-full bg-[var(--nav-active-indicator)] motion-reduce:hidden"
      aria-hidden="true"
    />
  </button>
</template>
