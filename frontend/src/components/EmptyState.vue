<template>
  <div class="empty-state-card" :class="[sizeClass, wrapClass]">
    <div v-if="illustrationSrc" class="empty-state-illus-wrap" aria-hidden="true">
      <img class="empty-state-illus" :src="illustrationSrc" :alt="illustrationAlt || ''" loading="lazy" decoding="async" />
    </div>
    <div class="empty-state-body">
      <h3 v-if="title" class="empty-state-title">{{ title }}</h3>
      <p v-if="resolvedText" class="empty-state-desc">{{ resolvedText }}</p>
      <div v-if="$slots.actions" class="empty-state-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  text?: string
  description?: string
  illustrationSrc?: string
  illustrationAlt?: string
  size?: 'md' | 'lg'
  wrapClass?: string
}>(), {
  title: '',
  text: '',
  description: '',
  illustrationSrc: '',
  illustrationAlt: '',
  size: 'md',
  wrapClass: '',
})

const resolvedText = computed(() => props.description || props.text || '')
const sizeClass = computed(() => (props.size === 'lg' ? 'empty-state-card--lg' : 'empty-state-card--md'))
</script>

<style scoped>
.empty-state-card {
  border-radius: 20px;
  border: var(--border-hairline);
  background: rgba(255, 255, 255, 0.02);
  box-shadow: 0 1px 0 rgba(0,0,0,0.08), 0 18px 40px rgba(0,0,0,0.22);
  padding: var(--space-6);
  display: grid;
  gap: var(--space-5);
  align-items: center;
}
.empty-state-card--lg { padding: var(--space-8); }

.empty-state-illus-wrap {
  display: flex;
  justify-content: center;
}
.empty-state-illus {
  width: 100%;
  max-width: 400px;
  height: auto;
  border-radius: 20px;
  filter: drop-shadow(0 18px 30px rgba(var(--primary-rgb), 0.10));
}
.empty-state-body { text-align: center; }
.empty-state-title {
  font-size: var(--font-section-title);
  font-weight: 650;
  letter-spacing: var(--tracking-tight);
  color: var(--text-primary);
  margin: 0;
}
.empty-state-desc {
  margin: var(--space-3) auto 0;
  max-width: 42rem;
  font-size: var(--font-body);
  color: var(--text-secondary);
  line-height: var(--line-normal);
}
.empty-state-actions {
  margin-top: var(--space-5);
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
}

@media (max-width: 640px) {
  .empty-state-illus { max-width: 260px; }
  .empty-state-card--lg { padding: var(--space-6); }
}
</style>

