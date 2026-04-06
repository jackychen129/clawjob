<template>
  <div class="claw-md" :class="{ 'claw-md--scroll': scrollMax }" v-html="html" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdownToSafeHtml } from '../utils/renderMarkdown'

const props = withDefaults(
  defineProps<{
    content: string
    /** Long feeds: cap height and scroll inside */
    scrollMax?: boolean
  }>(),
  { scrollMax: false }
)

const html = computed(() => renderMarkdownToSafeHtml(props.content || ''))
</script>

<style scoped>
.claw-md {
  font-size: inherit;
  line-height: 1.55;
  word-break: break-word;
}
.claw-md :deep(p) {
  margin: 0 0 0.5em;
}
.claw-md :deep(p:last-child) {
  margin-bottom: 0;
}
.claw-md :deep(ul),
.claw-md :deep(ol) {
  margin: 0.35em 0 0.5em;
  padding-left: 1.25rem;
}
.claw-md :deep(li) {
  margin: 0.15em 0;
}
.claw-md :deep(blockquote) {
  margin: 0.35em 0;
  padding-left: 0.75rem;
  border-left: 3px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary, rgba(255, 255, 255, 0.75));
}
.claw-md :deep(a) {
  color: var(--primary-color, #60a5fa);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.claw-md :deep(pre) {
  margin: 0.4em 0;
  padding: 0.5rem 0.65rem;
  border-radius: var(--radius-md, 6px);
  background: rgba(0, 0, 0, 0.35);
  overflow-x: auto;
  font-size: 0.9em;
}
.claw-md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.9em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
}
.claw-md :deep(pre code) {
  padding: 0;
  background: none;
}
.claw-md :deep(strong) {
  font-weight: 600;
}
.claw-md :deep(h1),
.claw-md :deep(h2),
.claw-md :deep(h3),
.claw-md :deep(h4) {
  margin: 0.5em 0 0.35em;
  font-size: 1em;
  font-weight: 600;
}
.claw-md--scroll {
  max-height: 14rem;
  overflow-y: auto;
}
</style>
