import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

export type AuthTab = 'login' | 'register'

export type AuthModalContext = {
  open: Ref<boolean>
  tab: Ref<AuthTab>
  openAuth: (tab?: AuthTab) => void
}

export const authModalKey: InjectionKey<AuthModalContext> = Symbol('authModal')

/** @deprecated Use openAuth from useAuthModal() */
export const showAuthModalKey: InjectionKey<Ref<boolean>> = Symbol('showAuthModal')

export function provideAuthModal() {
  const open = ref(false)
  const tab = ref<AuthTab>('login')

  function openAuth(nextTab?: AuthTab) {
    if (nextTab) tab.value = nextTab
    open.value = true
  }

  const ctx: AuthModalContext = { open, tab, openAuth }
  provide(authModalKey, ctx)
  provide(showAuthModalKey, open)
  return ctx
}

export function useAuthModal() {
  const ctx = inject(authModalKey, null)
  if (ctx) return ctx
  const open = inject(showAuthModalKey, ref(false))
  return {
    open,
    tab: ref<AuthTab>('login'),
    openAuth: (nextTab?: AuthTab) => {
      if (nextTab) {
        /* tab only available when full context is provided */
      }
      open.value = true
    },
  }
}
