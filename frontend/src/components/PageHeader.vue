<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '../lib/utils'

defineProps<{
  title: string
  description?: string
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <header
    :class="
      cn(
        'page-header mb-4 flex flex-col gap-3 border-b border-[var(--border-hairline)] pb-3 sm:flex-row sm:items-start sm:justify-between',
        $props.class,
      )
    "
  >
    <div class="page-header__main min-w-0 flex-1">
      <nav
        v-if="$slots.breadcrumbs"
        class="page-header__breadcrumbs mb-2 text-sm text-[var(--text-secondary)]"
        aria-label="Breadcrumb"
      >
        <slot name="breadcrumbs" />
      </nav>
      <h1
        class="page-header__title text-[length:var(--font-page-title)] font-bold tracking-[var(--tracking-tight)] text-[var(--text-primary)]"
      >
        {{ title }}
      </h1>
      <p
        v-if="description"
        class="page-header__desc mt-1 max-w-2xl text-sm text-[var(--text-secondary)]"
      >
        {{ description }}
      </p>
    </div>
    <div
      v-if="$slots.actions"
      class="page-header__actions flex shrink-0 flex-wrap items-center gap-2"
    >
      <slot name="actions" />
    </div>
  </header>
</template>
