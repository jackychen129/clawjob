<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

/** @deprecated Use /admin nested routes via AdminLayout */
const router = useRouter()
onMounted(() => router.replace('/admin'))
</script>

<template>
  <p class="hint">Redirecting to admin console…</p>
</template>
