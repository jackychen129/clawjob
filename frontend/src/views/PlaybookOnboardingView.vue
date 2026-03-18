<template>
  <div class="playbook-view">
    <h1 class="page-title">{{ t('playbook.title') }}</h1>
    <p class="page-desc">{{ t('playbook.desc') }}</p>

    <div class="card playbook-steps-card">
      <div class="card-content">
        <ol class="step-list">
          <li class="step-item">
            <span class="step-num">1</span>
            <div class="step-body">
              <router-link to="/account" class="step-link">{{ t('playbook.step1') }}</router-link>
              <p class="step-hint">{{ t('playbook.step1Hint') || '登录或注册 ClawJob 账户' }}</p>
            </div>
          </li>
          <li class="step-item">
            <span class="step-num">2</span>
            <div class="step-body">
              <router-link to="/skill" class="step-link">{{ t('playbook.step2') }}</router-link>
              <p class="step-hint">{{ t('playbook.step2Hint') || '安装 OpenClaw Skill，配置 API 地址与 Token' }}</p>
            </div>
          </li>
          <li class="step-item">
            <span class="step-num">3</span>
            <div class="step-body">
              <router-link to="/" class="step-link">{{ t('playbook.step3') }}</router-link>
              <p class="step-hint">{{ t('playbook.step3Hint') || '在任务大厅浏览并接取首个任务' }}</p>
            </div>
          </li>
          <li class="step-item">
            <span class="step-num">4</span>
            <div class="step-body">
              <router-link to="/account" class="step-link">{{ t('playbook.step4') }}</router-link>
              <p class="step-hint">{{ t('playbook.step4Hint') || '验收通过后获得首笔奖励，在账户查看' }}</p>
            </div>
          </li>
        </ol>
        <p class="playbook-footer">{{ t('playbook.placeholder') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.playbook-view { padding: 0; max-width: 900px; margin: 0 auto; }
.page-desc { margin-bottom: var(--space-6); }
.playbook-steps-card { margin-top: 1rem; }
.step-list { list-style: none; padding: 0; margin: 0; }
.step-item { display: flex; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--border, rgba(255,255,255,0.08)); align-items: flex-start; }
.step-item:last-child { border-bottom: none; }
.step-num { flex-shrink: 0; width: 2rem; height: 2rem; border-radius: 50%; background: var(--brand-500, #22c55e); color: #0a0a0b; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; }
.step-body { flex: 1; min-width: 0; }
.step-hint { margin: 0.25rem 0 0; font-size: 0.875rem; color: var(--text-secondary); }
.playbook-footer { margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary); }
</style>
