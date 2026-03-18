<template>
  <div class="rental-view">
    <h1 class="page-title">{{ t('rental.title') }}</h1>
    <p class="page-desc">{{ t('rental.desc') }}</p>
    <div class="card placeholder-card">
      <div class="card-content">
        <p>{{ t('rental.placeholder') }}</p>
        <ul class="feature-list">
          <li>{{ t('rental.escrow') }}</li>
          <li>{{ t('rental.skillPack') }}</li>
          <li>{{ t('rental.swarm') }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.rental-view { padding: 0; max-width: 900px; margin: 0 auto; }
.page-desc { margin-bottom: var(--space-6); }
.placeholder-card { margin-top: 1rem; }
.feature-list { margin-top: 0.75rem; padding-left: 1.25rem; color: var(--text-secondary); }
</style>
