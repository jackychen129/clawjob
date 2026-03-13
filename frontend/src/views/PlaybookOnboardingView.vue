<template>
  <div class="playbook-view">
    <h1 class="page-title">{{ t('playbook.title') }}</h1>
    <p class="page-desc">{{ t('playbook.desc') }}</p>
    <div class="card placeholder-card">
      <div class="card-content">
        <p>{{ t('playbook.placeholder') }}</p>
        <ol class="step-list">
          <li>{{ t('playbook.step1') }}</li>
          <li>{{ t('playbook.step2') }}</li>
          <li>{{ t('playbook.step3') }}</li>
          <li>{{ t('playbook.step4') }}</li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.playbook-view { padding: 1.5rem; max-width: 900px; margin: 0 auto; }
.page-title { font-size: 1.5rem; margin-bottom: 0.5rem; }
.page-desc { color: var(--el-text-color-secondary); margin-bottom: 1.5rem; font-size: 0.9rem; }
.placeholder-card { margin-top: 1rem; }
.step-list { margin-top: 0.75rem; padding-left: 1.25rem; color: var(--el-text-color-regular); }
</style>
