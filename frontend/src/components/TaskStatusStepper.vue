<script setup lang="ts">
import { Check, CircleDot, Clock, Loader, Wallet } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { cn } from '../lib/utils'

export type TaskStepperStatus =
  | 'open'
  | 'in_progress'
  | 'pending_verification'
  | 'completed'
  | 'settled'
  | 'disputed'

const props = withDefaults(
  defineProps<{
    status: TaskStepperStatus
    /** When true, terminal step shows settled instead of completed */
    settled?: boolean
    compact?: boolean
  }>(),
  {
    settled: false,
  },
)

const { t } = useI18n()

const steps = computed(() => {
  const terminal = props.settled ? 'settled' : 'completed'
  return [
    { id: 'open' as const, icon: CircleDot },
    { id: 'in_progress' as const, icon: Loader },
    { id: 'pending_verification' as const, icon: Clock },
    { id: terminal, icon: props.settled ? Wallet : Check },
  ]
})

const order = ['open', 'in_progress', 'pending_verification', 'completed', 'settled'] as const

const activeIndex = computed(() => {
  if (props.status === 'disputed') {
    const idx = order.indexOf('pending_verification')
    return idx >= 0 ? idx : 0
  }
  if (props.status === 'settled') return steps.value.length - 1
  if (props.status === 'completed') return steps.value.length - 1
  const idx = order.indexOf(props.status as (typeof order)[number])
  return idx >= 0 ? Math.min(idx, steps.value.length - 1) : 0
})

function stepState(index: number): 'done' | 'current' | 'upcoming' {
  if (index < activeIndex.value) return 'done'
  if (index === activeIndex.value) return 'current'
  return 'upcoming'
}

function stepLabel(id: string) {
  if (id === 'settled') return t('taskStepper.settled')
  if (id === 'completed') return t('taskStepper.completed')
  return t(`status.${id}` as 'status.open')
}
</script>

<template>
  <ol
    class="task-status-stepper flex w-full list-none flex-wrap items-center gap-0 p-0"
    :class="{ 'task-status-stepper--compact': compact }"
    aria-label="Task status"
  >
    <li
      v-for="(step, index) in steps"
      :key="step.id"
      class="task-status-stepper__step flex min-w-0 flex-1 items-center"
      :class="`task-status-stepper__step--${stepState(index)}`"
    >
      <div class="flex min-w-0 flex-col items-center gap-1 sm:flex-row sm:gap-2">
        <span
          :class="
            cn(
              'task-status-stepper__node flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-colors duration-[var(--duration-fast)] motion-reduce:transition-none',
              stepState(index) === 'done' &&
                'border-[rgba(var(--primary-rgb),0.4)] bg-[rgba(var(--primary-rgb),0.15)] text-[var(--primary-color)]',
              stepState(index) === 'current' &&
                'border-[var(--primary-color)] bg-[rgba(var(--primary-rgb),0.2)] text-[var(--primary-color)] shadow-[var(--shadow-layer-3)]',
              stepState(index) === 'upcoming' &&
                'border-[var(--border-color)] bg-[var(--surface-2)] text-[var(--text-tertiary)]',
            )
          "
          :aria-current="stepState(index) === 'current' ? 'step' : undefined"
        >
          <component :is="step.icon" class="h-4 w-4" aria-hidden="true" />
        </span>
        <span
          class="task-status-stepper__label max-w-[5.5rem] truncate text-center text-xs font-medium sm:max-w-none sm:text-left"
          :class="
            stepState(index) === 'current'
              ? 'text-[var(--text-primary)]'
              : 'text-[var(--text-secondary)]'
          "
        >
          {{ stepLabel(step.id) }}
        </span>
      </div>
      <span
        v-if="index < steps.length - 1"
        class="task-status-stepper__connector mx-1 hidden h-px flex-1 sm:block"
        :class="
          index < activeIndex
            ? 'bg-[var(--primary-color)]'
            : 'bg-[var(--border-color)]'
        "
        aria-hidden="true"
      />
    </li>
    <li
      v-if="status === 'disputed'"
      class="task-status-stepper__disputed ml-2 shrink-0 text-xs font-medium text-[#f97316]"
    >
      {{ t('status.disputed') }}
    </li>
  </ol>
</template>

<style scoped>
.task-status-stepper--compact .task-status-stepper__label {
  display: none;
}
@media (min-width: 640px) {
  .task-status-stepper--compact .task-status-stepper__label {
    display: block;
  }
}
</style>
