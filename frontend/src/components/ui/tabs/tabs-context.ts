import type { InjectionKey, Ref } from 'vue'

export type TabsContext = {
  modelValue: Ref<string>
  setValue: (v: string) => void
  baseId: string
}

export const tabsContextKey: InjectionKey<TabsContext> = Symbol('tabs')
