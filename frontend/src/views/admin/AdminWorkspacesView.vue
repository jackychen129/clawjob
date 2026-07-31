<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminDataTable from '../../components/admin/AdminDataTable.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const loading = ref(false)
const items = ref<Awaited<ReturnType<typeof api.listAdminWorkspaces>>['data']['items']>([])
const total = ref(0)
const skip = ref(0)
const pageSize = 50

const pageMeta = {
  get from() { return total.value ? skip.value + 1 : 0 },
  get to() { return skip.value + items.value.length },
  get total() { return total.value },
  get hasPrev() { return skip.value > 0 },
  get hasNext() { return skip.value + pageSize < total.value },
}

function reload(reset = false) {
  if (reset) skip.value = 0
  loading.value = true
  api.listAdminWorkspaces({ skip: skip.value, limit: pageSize })
    .then((res) => { items.value = res.data.items || []; total.value = res.data.total || 0 })
    .catch(() => { items.value = []; total.value = 0 })
    .finally(() => { loading.value = false })
}

function prevPage() {
  skip.value = Math.max(0, skip.value - pageSize)
  reload()
}

function nextPage() {
  skip.value += pageSize
  reload()
}

onMounted(() => reload(true))
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.workspacesTitle') || '企业工作区'"
      :description="t('admin.workspacesHint') || '平台全部 Workspace 席位与积分概览（D-17 运营视图）。'"
    />

    <AdminDataTable
      :loading="loading"
      :is-empty="items.length === 0"
      :empty-message="t('admin.workspacesEmpty') || '暂无工作区'"
      :page-from="pageMeta.from"
      :page-to="pageMeta.to"
      :page-total="pageMeta.total"
      :page-has-prev="pageMeta.hasPrev"
      :page-has-next="pageMeta.hasNext"
      @refresh="reload()"
      @prev="prevPage"
      @next="nextPage"
    >
      <template #head>
        <TableRow>
          <TableHead>{{ t('admin.workspaceColName') || '名称' }}</TableHead>
          <TableHead>{{ t('admin.workspaceColPlan') || '套餐' }}</TableHead>
          <TableHead>{{ t('admin.workspaceColSeats') || '席位' }}</TableHead>
          <TableHead>{{ t('admin.workspaceColCredits') || '积分' }}</TableHead>
          <TableHead>{{ t('admin.workspaceColOwner') || '所有者' }}</TableHead>
        </TableRow>
      </template>
      <TableRow v-for="ws in items" :key="ws.id">
        <TableCell>
          <div class="font-medium">{{ ws.name }}</div>
          <div class="admin-log-time font-mono">{{ ws.slug }} · #{{ ws.id }}</div>
        </TableCell>
        <TableCell class="font-mono text-sm">{{ ws.plan }}</TableCell>
        <TableCell class="font-mono">{{ ws.seats_used }} / {{ ws.seats }}</TableCell>
        <TableCell class="font-mono">{{ ws.credits }}</TableCell>
        <TableCell class="font-mono text-sm">uid={{ ws.owner_user_id }}</TableCell>
      </TableRow>
    </AdminDataTable>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
