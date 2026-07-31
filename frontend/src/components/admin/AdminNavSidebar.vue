<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Shield } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { safeT } from '../../i18n'
import type { AdminNavSection } from '../../composables/admin/useAdminNav'

const props = defineProps<{
  sections: AdminNavSection[]
  pendingTotal: number
  isActive: (item: { to: string; name: string }) => boolean
}>()

const emit = defineEmits<{ navigate: [] }>()

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const visibleSections = computed(() => props.sections.filter((s) => s.items.length > 0))
</script>

<template>
  <div class="admin-nav-sidebar">
    <div class="admin-nav-sidebar__brand">
      <Shield :size="18" aria-hidden="true" />
      <span>{{ t('admin.nav.console') || '运营控制台' }}</span>
      <span v-if="pendingTotal > 0" class="admin-nav-badge">{{ pendingTotal > 99 ? '99+' : pendingTotal }}</span>
    </div>
    <nav class="admin-nav-sidebar__sections" aria-label="Admin navigation">
      <section v-for="section in visibleSections" :key="section.id" class="admin-nav-section">
        <h3 class="admin-nav-section__label">{{ t(section.labelKey) }}</h3>
        <ul class="admin-nav-section__list">
          <li v-for="item in section.items" :key="item.to">
            <RouterLink
              :to="item.to"
              class="admin-nav-link"
              :class="{ 'admin-nav-link--active': isActive(item) }"
              @click="emit('navigate')"
            >
              <span class="admin-nav-link__left">
                <component :is="item.icon" :size="16" aria-hidden="true" />
                <span>{{ t(item.labelKey) }}</span>
              </span>
              <span v-if="item.badge && item.badge() > 0" class="admin-nav-badge">{{ item.badge() > 99 ? '99+' : item.badge() }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </nav>
  </div>
</template>
