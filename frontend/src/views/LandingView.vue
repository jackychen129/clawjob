<template>
  <div class="landing-shell">
    <iframe
      class="home-iframe"
      src="/home/index.html"
      title="ClawJob"
      loading="eager"
    />
    <nav class="landing-dock" aria-label="Enter product">
      <RouterLink class="landing-dock__cta" to="/tasks?onboarding=1">{{ t('landing.enterQuest') }}</RouterLink>
      <RouterLink class="landing-dock__link" to="/tasks?sort=reward&settlement=agent_direct">{{ t('landing.enterHall') }}</RouterLink>
      <RouterLink class="landing-dock__link" to="/join">{{ t('landing.enterJoin') }}</RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.landing-shell {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 100dvh;
}
.home-iframe {
  display: block;
  width: 100%;
  flex: 1;
  min-height: calc(100dvh - 3.25rem);
  height: calc(100dvh - 3.25rem);
  border: 0;
  margin: 0;
  padding: 0;
  background: #0a0a0b;
}
.landing-dock {
  position: sticky;
  bottom: 0;
  z-index: 20;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.75rem 1.25rem;
  min-height: 3.25rem;
  padding: 0.65rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 10, 11, 0.92);
  backdrop-filter: blur(12px);
}
.landing-dock__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 1rem;
  border-radius: 0.65rem;
  background: #e8e8ea;
  color: #0a0a0b;
  font-size: 0.875rem;
  font-weight: 700;
  text-decoration: none;
}
.landing-dock__cta:hover { filter: brightness(1.05); }
.landing-dock__link {
  color: rgba(250, 250, 250, 0.72);
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
}
.landing-dock__link:hover { color: #fafafa; }
</style>
