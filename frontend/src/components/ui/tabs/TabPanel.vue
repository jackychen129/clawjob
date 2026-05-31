<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, inject } from 'vue'
import { cn } from '../../../lib/utils'
import { tabsContextKey } from './tabs-context'

const props = defineProps<{
  value: string
  class?: HTMLAttributes['class']
}>()

const ctx = inject(tabsContextKey)
if (!ctx) throw new Error('TabPanel must be used within Tabs')

const selected = computed(() => ctx.modelValue.value === props.value)
const tabId = computed(() => `${ctx.baseId}-tab-${props.value}`)
const panelId = computed(() => `${ctx.baseId}-panel-${props.value}`)
</script>

<template>
  <div
    v-show="selected"
    :id="panelId"
    role="tabpanel"
    :aria-labelledby="tabId"
    :class="cn('ui-tab-panel focus:outline-none', props.class)"
    tabindex="0"
  >
    <slot />
  </div>
</template>
