<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { clearOAuthFromUrl, parseOAuthFromLocation, stashOAuthError } from '../lib/oauthCallback'

const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  const result = parseOAuthFromLocation()
  if (result.error) {
    stashOAuthError(result.error)
    clearOAuthFromUrl('#/tasks')
  } else if (result.token) {
    auth.setUser(result.token, result.username || 'user', result.userId)
    clearOAuthFromUrl('#/tasks')
  }
  await router.replace('/tasks')
})
</script>

<template>
  <div class="auth-callback" aria-live="polite">登录中…</div>
</template>

<style scoped>
.auth-callback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  color: var(--text-secondary, #a1a1aa);
  font-size: 1rem;
}
</style>
