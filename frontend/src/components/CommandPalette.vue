<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  BookOpen,
  Bot,
  FileText,
  LayoutGrid,
  ListTodo,
  MessagesSquare,
  Rocket,
  Shield,
  UserPlus,
  UserRound,
} from 'lucide-vue-next'
import { Dialog } from './ui/dialog'
import { cn } from '../lib/utils'

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  'publish-task': []
  'join-agent': []
}>()

const { t } = useI18n()
const router = useRouter()

type CommandItem = {
  id: string
  kind: 'navigate' | 'action'
  label: string
  keywords?: string
  icon?: typeof ListTodo
  run: () => void
}

const query = ref('')
const activeIndex = ref(0)
const listRef = ref<HTMLElement | null>(null)

const navItems = computed<CommandItem[]>(() => [
  {
    id: 'tasks',
    kind: 'navigate',
    label: t('nav.market'),
    keywords: 'tasks market hall',
    icon: ListTodo,
    run: () => router.push('/tasks'),
  },
  {
    id: 'community',
    kind: 'navigate',
    label: t('nav.community'),
    keywords: 'community chat forum',
    icon: MessagesSquare,
    run: () => router.push('/community'),
  },
  {
    id: 'agents',
    kind: 'navigate',
    label: t('nav.agentManage'),
    keywords: 'agents studio',
    icon: Bot,
    run: () => router.push('/agents'),
  },
  {
    id: 'account',
    kind: 'navigate',
    label: t('common.myAccount'),
    keywords: 'account profile settings',
    icon: UserRound,
    run: () => router.push('/account'),
  },
  {
    id: 'join',
    kind: 'navigate',
    label: t('nav.joinAgent'),
    keywords: 'join register agent',
    icon: UserPlus,
    run: () => router.push('/join'),
  },
  {
    id: 'agent-studio',
    kind: 'navigate',
    label: t('nav.agentStudio'),
    keywords: 'studio creator dashboard earnings',
    icon: Bot,
    run: () => router.push('/agent-studio'),
  },
  {
    id: 'dashboard',
    kind: 'navigate',
    label: t('nav.dashboard'),
    keywords: 'dashboard stats',
    icon: LayoutGrid,
    run: () => router.push('/dashboard'),
  },
  {
    id: 'playbook',
    kind: 'navigate',
    label: t('nav.playbook'),
    keywords: 'playbook start guide',
    icon: Rocket,
    run: () => router.push('/playbook'),
  },
  {
    id: 'docs',
    kind: 'navigate',
    label: t('common.docs'),
    keywords: 'docs manual documentation',
    icon: FileText,
    run: () => router.push('/docs'),
  },
  {
    id: 'admin',
    kind: 'navigate',
    label: t('nav.adminNav'),
    keywords: 'admin ops',
    icon: Shield,
    run: () => router.push('/admin'),
  },
])

const actionItems = computed<CommandItem[]>(() => [
  {
    id: 'publish-task',
    kind: 'action',
    label: t('commandPalette.publishTask'),
    keywords: 'publish post create task',
    icon: BookOpen,
    run: () => emit('publish-task'),
  },
  {
    id: 'join-agent-action',
    kind: 'action',
    label: t('commandPalette.joinAgent'),
    keywords: 'join register minimal agent',
    icon: UserPlus,
    run: () => emit('join-agent'),
  },
])

const allItems = computed(() => [...navItems.value, ...actionItems.value])

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return allItems.value
  return allItems.value.filter((item) => {
    const hay = `${item.label} ${item.keywords ?? ''} ${item.id}`.toLowerCase()
    return hay.includes(q)
  })
})

const navigateFiltered = computed(() =>
  filtered.value.filter((i) => i.kind === 'navigate'),
)
const actionFiltered = computed(() =>
  filtered.value.filter((i) => i.kind === 'action'),
)

watch(filtered, () => {
  if (activeIndex.value >= filtered.value.length) {
    activeIndex.value = Math.max(0, filtered.value.length - 1)
  }
})

function close() {
  open.value = false
}

function runItem(item: CommandItem) {
  item.run()
  close()
}

function onGlobalKeydown(event: KeyboardEvent) {
  const mod = event.metaKey || event.ctrlKey
  if (mod && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    open.value = !open.value
  }
}

function onPaletteKeydown(event: KeyboardEvent) {
  if (!open.value) return
  const len = filtered.value.length
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = len ? (activeIndex.value + 1) % len : 0
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = len ? (activeIndex.value - 1 + len) % len : 0
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const item = filtered.value[activeIndex.value]
    if (item) runItem(item)
  }
}

function flatIndex(group: 'navigate' | 'action', localIndex: number) {
  if (group === 'navigate') return localIndex
  return navigateFiltered.value.length + localIndex
}

function isActive(group: 'navigate' | 'action', localIndex: number) {
  return activeIndex.value === flatIndex(group, localIndex)
}

watch(open, (isOpen) => {
  if (typeof window === 'undefined') return
  if (isOpen) {
    query.value = ''
    activeIndex.value = 0
    window.addEventListener('keydown', onPaletteKeydown)
    nextTick(() => {
      const input = listRef.value?.querySelector<HTMLInputElement>(
        '[data-command-input]',
      )
      input?.focus()
    })
  } else {
    window.removeEventListener('keydown', onPaletteKeydown)
  }
})

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  window.removeEventListener('keydown', onPaletteKeydown)
})
</script>

<template>
  <Dialog
    v-model:open="open"
    class="max-w-xl gap-0 overflow-hidden p-0"
    overlay-class="bg-black/70"
  >
    <div ref="listRef" class="command-palette flex flex-col">
      <div class="border-b border-[var(--border-hairline)] px-4 py-3">
        <label class="sr-only" for="command-palette-input">{{
          t('commandPalette.placeholder')
        }}</label>
        <input
          id="command-palette-input"
          data-command-input
          v-model="query"
          type="search"
          autocomplete="off"
          spellcheck="false"
          class="w-full border-0 bg-transparent text-base text-[var(--text-primary)] outline-none placeholder:text-[var(--text-tertiary)]"
          :placeholder="t('commandPalette.placeholder')"
        />
        <p class="mt-2 text-xs text-[var(--text-tertiary)]">
          {{ t('commandPalette.shortcutHint') }}
        </p>
      </div>
      <div
        class="max-h-[min(60vh,24rem)] overflow-y-auto px-2 py-2"
        role="listbox"
        :aria-label="t('commandPalette.title')"
      >
        <template v-if="filtered.length">
          <section v-if="navigateFiltered.length" class="mb-2">
            <p
              class="px-2 py-1 text-xs font-semibold uppercase tracking-[var(--tracking-wide)] text-[var(--text-tertiary)]"
            >
              {{ t('commandPalette.navigate') }}
            </p>
            <button
              v-for="(item, idx) in navigateFiltered"
              :key="item.id"
              type="button"
              role="option"
              :aria-selected="isActive('navigate', idx)"
              :class="
                cn(
                  'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors duration-[var(--duration-fast)] motion-reduce:transition-none',
                  isActive('navigate', idx)
                    ? 'bg-[rgba(var(--primary-rgb),0.12)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)]',
                )
              "
              @click="runItem(item)"
              @mouseenter="activeIndex = flatIndex('navigate', idx)"
            >
              <component
                :is="item.icon"
                v-if="item.icon"
                class="h-4 w-4 shrink-0 opacity-80"
                aria-hidden="true"
              />
              <span>{{ item.label }}</span>
            </button>
          </section>
          <section v-if="actionFiltered.length">
            <p
              class="px-2 py-1 text-xs font-semibold uppercase tracking-[var(--tracking-wide)] text-[var(--text-tertiary)]"
            >
              {{ t('commandPalette.actions') }}
            </p>
            <button
              v-for="(item, idx) in actionFiltered"
              :key="item.id"
              type="button"
              role="option"
              :aria-selected="isActive('action', idx)"
              :class="
                cn(
                  'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors duration-[var(--duration-fast)] motion-reduce:transition-none',
                  isActive('action', idx)
                    ? 'bg-[rgba(var(--primary-rgb),0.12)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--surface-3)]',
                )
              "
              @click="runItem(item)"
              @mouseenter="activeIndex = flatIndex('action', idx)"
            >
              <component
                :is="item.icon"
                v-if="item.icon"
                class="h-4 w-4 shrink-0 opacity-80"
                aria-hidden="true"
              />
              <span>{{ item.label }}</span>
            </button>
          </section>
        </template>
        <p
          v-else
          class="px-4 py-8 text-center text-sm text-[var(--text-secondary)]"
        >
          {{ t('commandPalette.noResults') }}
        </p>
      </div>
    </div>
  </Dialog>
</template>
