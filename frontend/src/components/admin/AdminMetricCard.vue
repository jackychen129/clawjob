<script setup lang="ts">
import { Card, CardContent } from '../ui/card'
import { cn } from '../../lib/utils'

defineProps<{
  title: string
  value: string | number
  hint?: string
  variant?: 'default' | 'ops' | 'alert'
}>()
</script>

<template>
  <Card
    :class="
      cn(
        'admin-metric-card-v2 transition-shadow',
        variant === 'ops' && 'admin-metric-card-v2--ops',
        variant === 'alert' && 'admin-metric-card-v2--alert',
      )
    "
  >
    <CardContent class="p-5">
      <div class="admin-metric-title">{{ title }}</div>
      <div class="admin-metric-value">{{ value }}</div>
      <p v-if="hint" class="admin-metric-hint">{{ hint }}</p>
    </CardContent>
  </Card>
</template>
