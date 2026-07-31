import { ref, watch } from 'vue'

const PLATFORM_ADMIN_KEY_SESSION = 'clawjob_platform_admin_key'

export function usePlatformAdminKey() {
  const platformAdminKey = ref('')

  function load() {
    try {
      platformAdminKey.value = sessionStorage.getItem(PLATFORM_ADMIN_KEY_SESSION) || ''
      try { localStorage.removeItem(PLATFORM_ADMIN_KEY_SESSION) } catch { /* ignore */ }
    } catch {
      platformAdminKey.value = ''
    }
  }

  function persist() {
    try {
      const key = platformAdminKey.value.trim()
      if (key) sessionStorage.setItem(PLATFORM_ADMIN_KEY_SESSION, key)
    } catch { /* ignore */ }
  }

  load()

  watch(platformAdminKey, () => {
    const k = platformAdminKey.value.trim()
    if (k) persist()
  })

  return { platformAdminKey, load, persist }
}
