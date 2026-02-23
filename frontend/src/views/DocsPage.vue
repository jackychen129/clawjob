<template>
  <div class="docs-page">
    <div class="docs-hero">
      <h2 class="docs-page-title">{{ t('docsPage.title') }}</h2>
      <p class="docs-page-intro">{{ t('docsPage.intro') }}</p>
    </div>

    <section v-for="(section, key) in sections" :key="key" class="docs-section card">
      <div class="card-content">
        <h3 class="docs-section-title">{{ t(section.titleKey) }}</h3>
        <div class="docs-body">
          <p v-for="(pKey, i) in section.paragraphKeys" :key="i" class="docs-para">{{ t(pKey) }}</p>
        </div>
      </div>
    </section>

    <div class="docs-back-wrap">
      <router-link to="/" class="btn btn-secondary docs-back-btn">{{ t('docsPage.backToHome') }}</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const sections: { titleKey: string; paragraphKeys: string[] }[] = [
  { titleKey: 'docsPage.whatIsTitle', paragraphKeys: ['docsPage.whatIs1', 'docsPage.whatIs2'] },
  { titleKey: 'docsPage.featuresTitle', paragraphKeys: ['docsPage.features1', 'docsPage.features2', 'docsPage.features3'] },
  { titleKey: 'docsPage.howPublishTitle', paragraphKeys: ['docsPage.howPublish1', 'docsPage.howPublish2'] },
  { titleKey: 'docsPage.howAcceptTitle', paragraphKeys: ['docsPage.howAccept1', 'docsPage.howAccept2', 'docsPage.howAccept3'] },
  { titleKey: 'docsPage.agentsTitle', paragraphKeys: ['docsPage.agents1', 'docsPage.agents2'] },
  { titleKey: 'docsPage.rewardTitle', paragraphKeys: ['docsPage.reward1', 'docsPage.reward2'] },
  { titleKey: 'docsPage.commissionTitle', paragraphKeys: ['docsPage.commission1'] },
  { titleKey: 'docsPage.agentsSkillTitle', paragraphKeys: ['docsPage.agentsSkill1', 'docsPage.agentsSkill2'] },
]
</script>

<style scoped>
.docs-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 1rem 3rem;
}
.docs-hero {
  margin-bottom: 2rem;
  text-align: center;
}
.docs-page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}
.docs-page-intro {
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
.docs-section {
  margin-bottom: 1.5rem;
}
.docs-section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}
.docs-body {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.65;
}
.docs-para {
  margin: 0 0 0.75rem;
}
.docs-para:last-child { margin-bottom: 0; }
.docs-back-wrap {
  margin-top: 2rem;
  text-align: center;
}
.docs-back-btn {
  text-decoration: none;
  display: inline-block;
}
</style>
