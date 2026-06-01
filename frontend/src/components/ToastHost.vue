<template>
  <div class="toast-host" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast-stack">
      <div
        v-for="item in items"
        :key="item.id"
        class="toast-item"
        :class="`toast-item--${item.kind}`"
        role="status"
        @click="dismiss(item.id)"
      >
        <span class="toast-icon" aria-hidden="true">
          <template v-if="item.kind === 'success'">✓</template>
          <template v-else-if="item.kind === 'error'">!</template>
          <template v-else>i</template>
        </span>
        <span class="toast-msg">{{ item.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { useToast } from '../composables/useToast'

const { items, dismiss } = useToast()
</script>

<style scoped>
.toast-host {
  position: fixed;
  z-index: 1000;
  bottom: max(1rem, env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: none;
  width: min(92vw, 26rem);
}
.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0.7rem 0.95rem;
  border-radius: var(--radius-lg);
  background: var(--card-background, rgba(20, 20, 22, 0.96));
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-card-hover, 0 8px 28px rgba(0, 0, 0, 0.4));
  color: var(--text-primary);
  font-size: var(--font-body);
  cursor: pointer;
  backdrop-filter: blur(8px);
}
.toast-icon {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: var(--radius-full);
  font-weight: 700;
  font-size: 0.8rem;
}
.toast-item--success { border-color: rgba(34, 197, 94, 0.4); }
.toast-item--success .toast-icon { background: rgba(34, 197, 94, 0.16); color: #22c55e; }
.toast-item--error { border-color: rgba(239, 68, 68, 0.45); }
.toast-item--error .toast-icon { background: rgba(239, 68, 68, 0.16); color: #f87171; }
.toast-item--info .toast-icon { background: rgba(var(--primary-rgb, 59 130 246), 0.16); color: var(--primary-color); }
.toast-msg { flex: 1; line-height: 1.4; }

.toast-stack-enter-active,
.toast-stack-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.toast-stack-enter-from { opacity: 0; transform: translateY(10px) scale(0.97); }
.toast-stack-leave-to { opacity: 0; transform: translateY(6px) scale(0.98); }
@media (prefers-reduced-motion: reduce) {
  .toast-stack-enter-active,
  .toast-stack-leave-active { transition: none; }
}
</style>
