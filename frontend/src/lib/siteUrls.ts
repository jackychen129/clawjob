/**
 * Canonical public URLs — production links always use domain, never raw IP.
 */
const RAW_SITE_DOMAIN = import.meta.env.VITE_SITE_DOMAIN

export function getSiteDomain(): string {
  if (RAW_SITE_DOMAIN === '') return ''
  const trimmed = RAW_SITE_DOMAIN && String(RAW_SITE_DOMAIN).trim()
  return trimmed || 'clawjob.com.cn'
}

export function canonicalWwwUrl(path = '/'): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `https://${getSiteDomain()}${p}`
}

export function canonicalAppUrl(hashPath = ''): string {
  const h = hashPath.startsWith('#') ? hashPath : hashPath ? `#${hashPath.replace(/^\//, '')}` : ''
  return `https://app.${getSiteDomain()}/${h}`.replace(/\/#/, '/#').replace(/\/$/, h ? '/' : '')
}

export function canonicalApiUrl(path = ''): string {
  const p = path.startsWith('/') ? path : path ? `/${path}` : ''
  return `https://api.${getSiteDomain()}${p}`
}

export function canonicalSkillDocsUrl(): string {
  return canonicalWwwUrl('/skill/')
}

export function shouldRedirectIpToDomain(): string | null {
  if (typeof window === 'undefined') return null
  const siteDomain = getSiteDomain()
  if (!siteDomain) return null
  const host = window.location.hostname
  if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null
  if (host === siteDomain) return null
  const { pathname, search, hash, protocol } = window.location
  const target = `${protocol}//app.${siteDomain}${pathname}${search}${hash}`
  return target
}
