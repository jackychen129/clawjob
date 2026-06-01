import { reactive } from 'vue'

export type ToastKind = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  message: string
  kind: ToastKind
}

const state = reactive<{ items: ToastItem[] }>({ items: [] })
let seq = 0

function push(message: string, kind: ToastKind = 'info', durationMs = 2600) {
  const id = ++seq
  state.items.push({ id, message, kind })
  window.setTimeout(() => dismiss(id), durationMs)
  return id
}

function dismiss(id: number) {
  const idx = state.items.findIndex((t) => t.id === id)
  if (idx !== -1) state.items.splice(idx, 1)
}

/**
 * Lightweight global toast. Backed by a module-level reactive store so any
 * component can fire a toast; rendered once via <ToastHost /> in App.vue.
 */
export function useToast() {
  return {
    items: state.items,
    toast: push,
    success: (m: string, d?: number) => push(m, 'success', d),
    error: (m: string, d?: number) => push(m, 'error', d ?? 3600),
    info: (m: string, d?: number) => push(m, 'info', d),
    dismiss,
  }
}
