<script setup lang="ts">
import { computed, onMounted, provide, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { Menu, RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Sheet } from '../components/ui/sheet'
import AdminBreadcrumb from '../components/admin/AdminBreadcrumb.vue'
import AdminNavSidebar from '../components/admin/AdminNavSidebar.vue'
import AdminTableSkeleton from '../components/admin/AdminTableSkeleton.vue'
import { safeT } from '../i18n'
import { useAdminGate } from '../composables/admin/useAdminGate'
import { useAdminOverview } from '../composables/admin/useAdminOverview'
import { useAdminNav } from '../composables/admin/useAdminNav'
import { ADMIN_CONTEXT_KEY } from '../composables/admin/adminContext'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const route = useRoute()

const { denied, checking, check } = useAdminGate()
const { overview, pendingCounts, loading: overviewLoading, refresh: refreshOverview } = useAdminOverview()
const { sections, isActive } = useAdminNav(pendingCounts)
const mobileNavOpen = ref(false)

provide(ADMIN_CONTEXT_KEY, { overview, refreshOverview })

const lastUpdated = computed(() => {
  const at = overview.value?.generated_at
  if (!at) return ''
  return at.slice(0, 19).replace('T', ' ')
})

async function refreshAll() {
  await refreshOverview()
}

function onNavClick() {
  mobileNavOpen.value = false
}

onMounted(async () => {
  await check()
  if (!denied.value) await refreshOverview()
})
</script>

<template>
  <section class="admin-wrap-v2 apple-layout">
    <div v-if="checking" class="admin-gate-state">
      <Card>
        <CardContent class="p-6">
          <AdminTableSkeleton :rows="3" />
        </CardContent>
      </Card>
    </div>

    <div v-else-if="denied" class="admin-gate-state">
      <Card>
        <CardContent class="p-6">
          <p class="error-msg">{{ t('admin.denied') || '无权限访问（需要管理员账号）' }}</p>
        </CardContent>
      </Card>
    </div>

    <div v-else class="admin-shell-v2">
      <aside class="admin-shell-v2__sidebar" aria-label="Admin navigation">
        <AdminNavSidebar
          :sections="sections"
          :pending-total="pendingCounts.total"
          :is-active="isActive"
          @navigate="onNavClick"
        />
      </aside>

      <Sheet v-model:open="mobileNavOpen" side="left" :title="t('admin.nav.console') || '运营控制台'">
        <AdminNavSidebar
          :sections="sections"
          :pending-total="pendingCounts.total"
          :is-active="isActive"
          @navigate="onNavClick"
        />
      </Sheet>

      <div class="admin-shell-v2__main">
        <header class="admin-topbar">
          <div class="admin-topbar__left">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="admin-topbar__menu"
              :aria-label="t('admin.openNav') || '打开导航'"
              @click="mobileNavOpen = true"
            >
              <Menu :size="18" />
            </Button>
            <AdminBreadcrumb />
          </div>
          <div class="admin-topbar__right">
            <span v-if="lastUpdated" class="admin-topbar__meta">
              {{ t('admin.generatedAt') || '更新' }} · {{ lastUpdated }}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              class="admin-topbar__refresh"
              :aria-label="t('common.retry') || '刷新'"
              :disabled="overviewLoading"
              @click="refreshAll"
            >
              <RefreshCw :size="14" class="admin-topbar__refresh-icon" :class="{ 'admin-topbar__refresh-icon--spin': overviewLoading }" />
              <span class="admin-topbar__refresh-label">{{ t('common.retry') || '刷新' }}</span>
            </Button>
          </div>
        </header>

        <main class="admin-main-v2">
          <RouterView v-slot="{ Component }">
            <Transition name="admin-page" mode="out-in">
              <component :is="Component" :key="route.fullPath" />
            </Transition>
          </RouterView>
        </main>
      </div>
    </div>
  </section>
</template>

<style scoped>
.admin-topbar__refresh-icon--spin {
  animation: admin-spin 0.8s linear infinite;
}
@keyframes admin-spin {
  to { transform: rotate(360deg); }
}
</style>
