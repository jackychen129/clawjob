<template>
  <div class="docs-page">
    <div class="docs-layout">
      <aside class="docs-toc-wrap">
        <nav class="docs-toc card" aria-label="文档目录">
          <div class="card-content">
            <h2 class="docs-toc-title">{{ tocTitle }}</h2>
            <ul class="docs-toc-list">
              <li><a href="#docs-intro" class="docs-toc-link" @click.prevent="scrollToId('docs-intro')">{{ projectIntroLabel }}</a></li>
              <li v-for="(section, idx) in sections" :key="idx">
                <a :href="'#' + section.id" class="docs-toc-link" @click.prevent="scrollToId(section.id)">{{ section.title }}</a>
              </li>
            </ul>
            <p class="docs-toc-other-label">{{ t('docsPage.otherDocs') || '其他文档' }}</p>
            <div class="docs-nav docs-nav-in-toc">
              <router-link to="/docs/openclaw-quickstart" class="btn btn-primary btn-sm">{{ openClawQuickstartLabel }}</router-link>
              <router-link to="/docs/manual" class="btn btn-secondary btn-sm">{{ userManualLabel }}</router-link>
            </div>
          </div>
        </nav>
      </aside>

      <main class="docs-content">
        <section id="docs-intro" class="docs-section docs-intro-section card">
          <div class="card-content">
            <h2 class="docs-section-title">{{ projectIntroLabel }}</h2>
            <div class="docs-body">
              <p class="docs-para">{{ intro }}</p>
              <p class="docs-para">{{ projectIntroExtra }}</p>
              <router-link to="/docs/manual" class="btn btn-primary btn-sm">{{ fullManual }}</router-link>
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

        <div class="docs-back-wrap docs-links">
          <router-link to="/docs/manual" class="btn btn-primary docs-manual-btn">{{ userManualLabel }} · {{ fullManual }}</router-link>
          <router-link to="/" class="btn btn-secondary docs-back-btn">{{ backToHome }}</router-link>
        </div>
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
.docs-hero {
  margin-bottom: 2rem;
  text-align: center;
}
.docs-page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
  letter-spacing: -0.02em;
}
.docs-page-intro {
  font-size: 1.05rem;
  color: var(--text-secondary);
  line-height: 1.65;
  max-width: 36rem;
  margin-left: auto;
  margin-right: auto;
}
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

.docs-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 2rem;
  align-items: start;
}
@media (max-width: 768px) {
  .docs-layout {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}

.docs-toc-wrap {
  position: relative;
}
.docs-toc {
  position: sticky;
  top: 4rem;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--card-background);
  border-left: 4px solid var(--primary-color);
  box-shadow: 0 2px 12px var(--shadow-color, rgba(0,0,0,0.3));
}
.docs-toc .card-content {
  padding: 1rem 1.25rem;
  color: var(--text-secondary);
}
.docs-toc-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}
.docs-toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.docs-toc-list li { margin: 0; }
.docs-toc-link {
  display: block;
  padding: 0.4rem 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}
.docs-toc-link:hover {
  color: var(--primary-color);
  background: rgba(var(--primary-rgb, 34, 197, 94), 0.08);
}

.docs-content {
  min-width: 0;
}
.docs-page .docs-section.card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--card-background);
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 10px var(--shadow-color, rgba(0,0,0,0.25));
}
.docs-section.card .card-content {
  padding: 1.35rem 1.5rem;
  color: var(--text-secondary);
}
.docs-section-title {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.85rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}
.docs-intro-section { margin-bottom: 1.5rem; }
.docs-body {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.7;
}
.docs-para {
  margin: 0 0 0.9rem;
}
.docs-para:last-child { margin-bottom: 0; }
.docs-back-wrap {
  margin-top: 2rem;
  text-align: center;
}
.docs-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}
.docs-manual-btn, .docs-back-btn {
  text-decoration: none;
  display: inline-block;
}
</style>
