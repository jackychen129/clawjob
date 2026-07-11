/**
 * Canonical public URLs — production links always use domain, never raw IP.
 */
const RAW_SITE_DOMAIN = import.meta.env.VITE_SITE_DOMAIN

export function getSiteDomain(): string {
  if (RAW_SITE_DOMAIN === '') return ''
  const trimmed = RAW_SITE_DOMAIN && String(RAW_SITE_DOMAIN).trim()
  return trimmed || 'clawjob.com.cn'
}

/** Same-origin app base (works on clawjob.com.cn and app.clawjob.com.cn). */
export function appOrigin(): string {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin.replace(/\/$/, '')
  }
  const domain = getSiteDomain()
  return domain ? `https://${domain}` : 'https://clawjob.com.cn'
}

export function canonicalWwwUrl(path = '/'): string {
  const domain = getSiteDomain()
  if (!path || path === '/') {
    return `https://${domain}/#/`
  }
  const p = path.startsWith('/') ? path : `/${path}`
  return `https://${domain}/#${p}`
}

export function canonicalAppUrl(hashPath = '/tasks'): string {
  const p = hashPath.startsWith('/') ? hashPath : hashPath ? `/${hashPath}` : '/tasks'
  return canonicalWwwUrl(p)
}

export function canonicalApiUrl(path = ''): string {
  const p = path.startsWith('/') ? path : path ? `/${path}` : ''
  return `https://api.${getSiteDomain()}${p}`
}

export function canonicalSkillDocsUrl(): string {
  return canonicalWwwUrl('/skill')
}

export function canonicalSkillMdUrl(): string {
  return `${appOrigin()}/skill.md`
}

export function shouldRedirectIpToDomain(): string | null {
  if (typeof window === 'undefined') return null
  const siteDomain = getSiteDomain()
  if (!siteDomain) return null
  const host = window.location.hostname
  if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null
  if (host === siteDomain) return null
  const { pathname, search, hash, protocol } = window.location
  return `${protocol}//${siteDomain}${pathname}${search}${hash}`
}
