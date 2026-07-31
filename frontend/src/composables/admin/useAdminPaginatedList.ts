import { computed, ref } from 'vue'

export type AdminPageResult<T> = {
  items: T[]
  total: number
}

export function useAdminPaginatedList<T>(
  fetchPage: (params: { skip: number; limit: number }) => Promise<AdminPageResult<T>>,
  pageSize = 50,
) {
  const loading = ref(false)
  const items = ref([] as T[])
  const total = ref(0)
  const skip = ref(0)

  async function reload(reset = false) {
    if (reset) skip.value = 0
    loading.value = true
    try {
      const res = await fetchPage({ skip: skip.value, limit: pageSize })
      items.value = res.items ?? []
      total.value = res.total ?? 0
    } catch {
      items.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  function prevPage() {
    if (skip.value <= 0) return
    skip.value = Math.max(0, skip.value - pageSize)
    return reload()
  }

  function nextPage() {
    if (skip.value + pageSize >= total.value) return
    skip.value += pageSize
    return reload()
  }

  const pageMeta = computed(() => ({
    from: total.value ? skip.value + 1 : 0,
    to: skip.value + items.value.length,
    total: total.value,
    hasPrev: skip.value > 0,
    hasNext: skip.value + pageSize < total.value,
  }))

  return {
    loading,
    items,
    total,
    skip,
    pageSize,
    pageMeta,
    reload,
    prevPage,
    nextPage,
  }
}
