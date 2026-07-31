import { ref } from 'vue'
import * as api from '../../api'

export function useAdminGate() {
  const denied = ref(false)
  const checking = ref(true)

  async function check() {
    checking.value = true
    denied.value = false
    try {
      await api.getAdminMe()
    } catch {
      denied.value = true
    } finally {
      checking.value = false
    }
    return !denied.value
  }

  return { denied, checking, check }
}
