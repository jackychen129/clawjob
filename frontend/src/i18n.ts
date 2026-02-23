import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import en from './locales/en'

const LOCALE_KEY = 'clawjob_locale'

const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(LOCALE_KEY) : null
const defaultLocale = saved === 'en' || saved === 'zh-CN' ? saved : 'en'

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
}

export type LocaleKey = 'zh-CN' | 'en'
