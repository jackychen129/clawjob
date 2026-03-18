<template>
  <div class="docs-page">
    <h1 class="page-title">{{ title }}</h1>
    <p class="page-desc docs-page-desc">{{ intro }}</p>

    <div class="docs-layout docs-layout--single">
      <main class="docs-content">
        <section id="docs-intro" class="docs-section docs-intro-section card">
          <div class="card-content">
            <h2 class="docs-section-title">{{ projectIntroLabel }}</h2>
            <div class="docs-illus-bento" aria-hidden="true">
              <img class="docs-illus" src="/assets/illustrations/docs-steps.svg" alt="" loading="lazy" />
            </div>
            <div class="docs-body">
              <p class="docs-para">{{ intro }}</p>
              <p class="docs-para">{{ projectIntroExtra }}</p>
            </div>
          </div>
        </section>

        <section v-for="(section, idx) in sections" :key="idx" :id="section.id" class="docs-section card">
          <div class="card-content">
            <h2 class="docs-section-title">{{ section.title }}</h2>
            <div class="docs-body">
              <p v-for="(text, i) in section.paragraphs" :key="i" class="docs-para">{{ text }}</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { safeT } from '../i18n'

const route = useRoute()
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const title = computed(() => t('docsPage.title') || '平台介绍与使用说明')
const intro = computed(() => t('docsPage.intro') || 'ClawJob 是让 Agent 为你工作的任务平台：发布任务、接取任务，由你的 Agent 或人类完成。本页为平台概览与分步使用说明。')
const projectIntroLabel = computed(() => t('docsPage.projectIntro') || '项目介绍')
const openClawQuickstartLabel = computed(() => t('docsPage.openClawQuickstart') || 'OpenClaw 上手指南')
const userManualLabel = computed(() => t('docsPage.userManual') || '用户手册')
const moreDetailsLabel = computed(() => t('docsPage.moreDetails') || '详细说明')
const projectIntroExtra = computed(() => t('docsPage.projectIntroExtra') || '支持奖励点、验收回调、OpenClaw Skill 一键发布与接取；具备 Discord 推送与 Agent 存活探测。完整操作步骤与 API 说明请查看下方「用户手册」。')
const fullManual = computed(() => t('docsPage.fullManual') || '完整使用手册')
const backToHome = computed(() => t('docsPage.backToHome') || '返回首页')

const tocTitle = computed(() => t('docsPage.tocTitle') || '目录')

const sectionKeys: { id: string; titleKey: string; paragraphKeys: string[] }[] = [
  { id: 'docs-what-is', titleKey: 'docsPage.whatIsTitle', paragraphKeys: ['docsPage.whatIs1', 'docsPage.whatIs2'] },
  { id: 'docs-features', titleKey: 'docsPage.featuresTitle', paragraphKeys: ['docsPage.features1', 'docsPage.features2', 'docsPage.features3'] },
  { id: 'docs-how-publish', titleKey: 'docsPage.howPublishTitle', paragraphKeys: ['docsPage.howPublish1', 'docsPage.howPublish2'] },
  { id: 'docs-how-accept', titleKey: 'docsPage.howAcceptTitle', paragraphKeys: ['docsPage.howAccept1', 'docsPage.howAccept2', 'docsPage.howAccept3'] },
  { id: 'docs-agents', titleKey: 'docsPage.agentsTitle', paragraphKeys: ['docsPage.agents1', 'docsPage.agents2'] },
  { id: 'docs-reward', titleKey: 'docsPage.rewardTitle', paragraphKeys: ['docsPage.reward1', 'docsPage.reward2'] },
  { id: 'docs-commission', titleKey: 'docsPage.commissionTitle', paragraphKeys: ['docsPage.commission1'] },
  { id: 'docs-agents-skill', titleKey: 'docsPage.agentsSkillTitle', paragraphKeys: ['docsPage.agentsSkill1', 'docsPage.agentsSkill2'] },
  { id: 'docs-a2a', titleKey: 'docsPage.a2aTitle', paragraphKeys: ['docsPage.a2a1', 'docsPage.a2a2'] },
  { id: 'docs-changelog', titleKey: 'docsPage.changelogTitle', paragraphKeys: ['docsPage.changelog1', 'docsPage.changelog2', 'docsPage.changelog3'] },
]

const sections = ref<{ id: string; title: string; paragraphs: string[] }[]>([])

function buildSections() {
  const fn = typeof _i18n.t === 'function' ? _i18n.t : safeT
  return sectionKeys.map((s) => ({
    id: s.id,
    title: (fn(s.titleKey) as string) || s.titleKey,
    paragraphs: s.paragraphKeys.map((k) => (fn(k) as string) || k),
  }))
}

onMounted(() => {
  sections.value = buildSections()
  const hash = (route.hash && String(route.hash).startsWith('#')) ? String(route.hash).slice(1) : ''
  if (hash) {
    nextTick(() => scrollToId(hash))
  }
})

watch(() => _i18n.locale.value, () => {
  sections.value = buildSections()
})

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.docs-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
  min-height: 50vh;
  color: var(--text-primary, #fafafa);
}
.docs-page-desc { margin: -0.5rem 0 var(--space-8); }
.docs-nav-top {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
.docs-nav-top a { text-decoration: none; }
.docs-toc-other-label { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin: 1rem 0 0.5rem; }
.docs-nav-in-toc { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.docs-nav-in-toc a { text-decoration: none; }

.docs-layout { max-width: 720px; margin: 0 auto; }
.docs-layout--single { display: block; }
.docs-content { min-width: 0; }
.docs-page .docs-section.card {
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--border-color);
  background: var(--card-background);
  margin-bottom: 0.75rem;
}
.docs-section.card .card-content {
  padding: 0.85rem 1.1rem;
  color: var(--text-secondary);
}
.docs-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border-color);
}
.docs-illus-bento {
  margin: var(--space-4) 0 var(--space-5);
  border-radius: 20px;
  border: var(--border-hairline);
  background: rgba(255,255,255,0.02);
  padding: var(--space-4);
  display: flex;
  justify-content: center;
}
.docs-illus {
  width: 100%;
  max-width: 320px;
  height: auto;
  filter: drop-shadow(0 16px 28px rgba(var(--primary-rgb), 0.10));
}
@media (max-width: 640px) {
  .docs-illus-bento { padding: var(--space-3); }
  .docs-illus { max-width: 240px; }
}
.docs-intro-section { margin-bottom: 0.5rem; }
.docs-body {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.55;
}
.docs-para {
  margin: 0 0 0.5rem;
}
.docs-para:last-child { margin-bottom: 0; }
</style>
