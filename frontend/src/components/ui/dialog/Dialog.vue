<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import {
  computed,
  nextTick,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { getFocusableElements, trapTabKey } from '../../../lib/focus-trap'
import { usePrefersReducedMotion } from '../../../lib/use-prefers-reduced-motion'
import { cn } from '../../../lib/utils'

const props = withDefaults(
  defineProps<{
    open?: boolean
    title?: string
    description?: string
    class?: HTMLAttributes['class']
    overlayClass?: HTMLAttributes['class']
    closeOnOverlay?: boolean
    closeOnEscape?: boolean
  }>(),
  {
    open: false,
    closeOnOverlay: true,
    closeOnEscape: true,
  },
)

const emit = defineEmits<{
  'update:open': [value: boolean]
  close: []
}>()

const reducedMotion = usePrefersReducedMotion()
const panelRef = ref<HTMLElement | null>(null)
const previousFocus = ref<HTMLElement | null>(null)

const transitionName = computed(() =>
  reducedMotion.value ? '' : 'ui-dialog',
)

function close() {
  emit('update:open', false)
  emit('close')
}

function onOverlayClick() {
  if (props.closeOnOverlay) close()
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (props.closeOnEscape && event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (panelRef.value) trapTabKey(event, panelRef.value)
}

watch(
  () => props.open,
  async (isOpen) => {
    if (typeof document === 'undefined') return
    if (isOpen) {
      previousFocus.value = document.activeElement as HTMLElement | null
      document.body.style.overflow = 'hidden'
      await nextTick()
      const items = panelRef.value
        ? getFocusableElements(panelRef.value)
        : []
      items[0]?.focus()
    } else {
      document.body.style.overflow = ''
      previousFocus.value?.focus?.()
      previousFocus.value = null
    }
  },
)

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition :name="transitionName">
      <div
        v-if="open"
        class="ui-dialog-root fixed inset-0 z-[100] flex items-center justify-center p-4"
        @keydown="onKeydown"
      >
        <div
          class="ui-dialog-overlay absolute inset-0 bg-black/60 backdrop-blur-sm motion-reduce:backdrop-blur-none"
          :class="overlayClass"
          aria-hidden="true"
          @click="onOverlayClick"
        />
        <div
          ref="panelRef"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="title ? 'ui-dialog-title' : undefined"
          :aria-describedby="description ? 'ui-dialog-desc' : undefined"
          :class="
            cn(
              'ui-dialog-panel relative z-[1] w-full max-w-lg rounded-[var(--radius-lg)] border border-[var(--border-muted-strong)] bg-[var(--surface-2)] p-6 text-[var(--text-primary)] shadow-[var(--shadow-layer-2)]',
              props.class,
            )
          "
          @click.stop
        >
          <header v-if="title || $slots.header" class="mb-4">
            <slot name="header">
              <h2
                v-if="title"
                id="ui-dialog-title"
                class="text-lg font-semibold tracking-[var(--tracking-tight)]"
              >
                {{ title }}
              </h2>
              <p
                v-if="description"
                id="ui-dialog-desc"
                class="mt-1 text-sm text-[var(--text-secondary)]"
              >
                {{ description }}
              </p>
            </slot>
          </header>
          <slot />
          <footer v-if="$slots.footer" class="mt-6 flex justify-end gap-2">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-dialog-enter-active,
.ui-dialog-leave-active {
  transition: opacity var(--duration-m) var(--ease-apple);
}
.ui-dialog-enter-active .ui-dialog-panel,
.ui-dialog-leave-active .ui-dialog-panel {
  transition:
    opacity var(--duration-m) var(--ease-apple),
    transform var(--duration-m) var(--ease-apple);
}
.ui-dialog-enter-from,
.ui-dialog-leave-to {
  opacity: 0;
}
.ui-dialog-enter-from .ui-dialog-panel,
.ui-dialog-leave-to .ui-dialog-panel {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}
</style>
