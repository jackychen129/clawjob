<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'

defineProps<{
  curl: string
  copied: boolean
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  copy: []
}>()

const { t } = useI18n()
</script>

<template>
  <div v-if="open" class="modal-mask" @click.self="open = false">
    <div class="modal modal--guest-register">
      <h3>{{ t('auth.guestRegisterModalTitle') }}</h3>
      <p class="hint">{{ t('auth.guestRegisterModalDesc') }}</p>
      <pre class="guest-register-curl"><code>{{ curl }}</code></pre>
      <div class="guest-register-actions">
        <Button type="button" @click="emit('copy')">{{ copied ? t('skillPage.copied') : t('auth.copyRegisterCurl') }}</Button>
        <Button as="router-link" to="/join" variant="secondary" @click="open = false">{{ t('nav.joinAgent') }}</Button>
        <Button variant="ghost" type="button" @click="open = false">{{ t('common.close') }}</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.guest-register-curl {
  margin: var(--space-4) 0;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.25);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  font-size: 0.85rem;
  overflow-x: auto;
}
.guest-register-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
