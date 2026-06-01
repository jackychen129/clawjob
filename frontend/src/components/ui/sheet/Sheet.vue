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
    side?: 'left' | 'right'
    title?: string
    class?: HTMLAttributes['class']
    closeOnOverlay?: boolean
    closeOnEscape?: boolean
  }>(),
  {
    open: false,
    side: 'left',
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
  reducedMotion.value ? '' : `ui-sheet-${props.side}`,
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
        class="ui-sheet-root fixed inset-0 z-[120] flex"
        :class="side === 'right' ? 'justify-end' : 'justify-start'"
        @keydown="onKeydown"
      >
        <div
          class="ui-sheet-overlay absolute inset-0 bg-black/50 backdrop-blur-[var(--header-blur)] motion-reduce:backdrop-blur-none"
          aria-hidden="true"
          @click="onOverlayClick"
        />
        <aside
          ref="panelRef"
          role="dialog"
          aria-modal="true"
          :aria-label="title || 'Navigation'"
          :class="
            cn(
              'ui-sheet-panel relative z-[1] flex h-full w-[min(100%,20rem)] flex-col border-[var(--border-muted-strong)] bg-[var(--surface-1)] shadow-[var(--shadow-layer-2)]',
              side === 'left' ? 'border-r' : 'border-l',
              props.class,
            )
          "
          @click.stop
        >
          <header
            v-if="title || $slots.header"
            class="flex shrink-0 items-center justify-between border-b border-[var(--border-hairline)] px-4 py-3"
          >
            <slot name="header">
              <h2
                v-if="title"
                class="text-base font-semibold tracking-[var(--tracking-tight)] text-[var(--text-primary)]"
              >
                {{ title }}
              </h2>
            </slot>
          </header>
          <div class="min-h-0 flex-1 overflow-y-auto p-4">
            <slot />
          </div>
          <footer
            v-if="$slots.footer"
            class="shrink-0 border-t border-[var(--border-hairline)] p-4"
          >
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-sheet-left-enter-active,
.ui-sheet-left-leave-active,
.ui-sheet-right-enter-active,
.ui-sheet-right-leave-active {
  transition: opacity var(--duration-m) var(--ease-apple);
}
.ui-sheet-left-enter-active .ui-sheet-panel,
.ui-sheet-left-leave-active .ui-sheet-panel {
  transition: transform var(--duration-m) var(--ease-apple);
}
.ui-sheet-right-enter-active .ui-sheet-panel,
.ui-sheet-right-leave-active .ui-sheet-panel {
  transition: transform var(--duration-m) var(--ease-apple);
}
.ui-sheet-left-enter-from,
.ui-sheet-left-leave-to,
.ui-sheet-right-enter-from,
.ui-sheet-right-leave-to {
  opacity: 0;
}
.ui-sheet-left-enter-from .ui-sheet-panel,
.ui-sheet-left-leave-to .ui-sheet-panel {
  transform: translateX(-100%);
}
.ui-sheet-right-enter-from .ui-sheet-panel,
.ui-sheet-right-leave-to .ui-sheet-panel {
  transform: translateX(100%);
}
</style>
