<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, provide } from 'vue'
import { cn } from '../../../lib/utils'
import { tabsContextKey } from './tabs-context'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    defaultValue?: string
    class?: HTMLAttributes['class']
  }>(),
  {
    defaultValue: '',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const baseId = `tabs-${Math.random().toString(36).slice(2, 9)}`

const current = computed({
  get: () => props.modelValue ?? props.defaultValue ?? '',
  set: (v: string) => emit('update:modelValue', v),
})

provide(tabsContextKey, {
  modelValue: computed(() => current.value),
  setValue: (v: string) => {
    current.value = v
  },
  baseId,
})
</script>

<template>
  <div :class="cn('ui-tabs flex flex-col gap-4', props.class)">
    <slot />
  </div>
</template>
