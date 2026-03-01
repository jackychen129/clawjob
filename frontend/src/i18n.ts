import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import en from './locales/en'

const LOCALE_KEY = 'clawjob_locale'

function getDefaultLocale(): 'zh-CN' | 'en' {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem(LOCALE_KEY)
    if (saved === 'en' || saved === 'zh-CN') return saved
  }
  if (typeof navigator !== 'undefined' && navigator.language) {
    if (navigator.language.startsWith('zh')) return 'zh-CN'
  }
  return 'en'
}

const defaultLocale = getDefaultLocale()

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: 'en',
  messages: {
    'zh-CN': zhCN,
    en,
  },
})

export function setLocale(locale: 'zh-CN' | 'en') {
  i18n.global.locale.value = locale
  try {
    localStorage.setItem(LOCALE_KEY, locale)
  } catch (_) {}
  applyLocaleToDocument(locale)
}

/** 将当前语言应用到 document（html lang、title），用于多语言与无障碍 */
export function applyLocaleToDocument(locale: 'zh-CN' | 'en') {
  if (typeof document === 'undefined') return
  document.documentElement.lang = locale === 'zh-CN' ? 'zh-CN' : 'en'
  const t = i18n.global.t
  if (typeof t === 'function') {
    document.title = t('common.pageTitle') as string
  }
}

/** 始终可调用的 t：避免生产构建中 useI18n().t 偶发非函数导致 "Oe is not a function" */
export function safeT(key: string, ...args: unknown[]): string {
  try {
    const fn = i18n.global.t
    if (typeof fn === 'function') return fn(key, ...args) as string
  } catch (_) {}
  return key
}

export type LocaleKey = 'zh-CN' | 'en'
