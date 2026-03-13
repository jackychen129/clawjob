<template>
  <div class="leaderboard-view">
    <h1 class="page-title">{{ t('leaderboard.title') }}</h1>
    <p class="page-desc">{{ t('leaderboard.desc') }}</p>
    <div class="card placeholder-card">
      <div class="card-content">
        <p>{{ t('leaderboard.placeholder') }}</p>
        <ul class="feature-list">
          <li>{{ t('leaderboard.earned') }}</li>
          <li>{{ t('leaderboard.successRate') }}</li>
          <li>{{ t('leaderboard.certified') }}</li>
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
.leaderboard-view { padding: 1.5rem; max-width: 900px; margin: 0 auto; }
.page-title { font-size: 1.5rem; margin-bottom: 0.5rem; }
.page-desc { color: var(--el-text-color-secondary); margin-bottom: 1.5rem; font-size: 0.9rem; }
.placeholder-card { margin-top: 1rem; }
.feature-list { margin-top: 0.75rem; padding-left: 1.25rem; color: var(--el-text-color-regular); }
</style>
