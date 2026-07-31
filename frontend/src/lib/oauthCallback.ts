/**
 * Parse Google OAuth redirect params from the current URL (hash or query).
 * Hash format is preferred for createWebHashHistory SPAs.
 */
export interface OAuthRedirectResult {
  error?: string
  token?: string
  username?: string
  userId?: number
}

const OAUTH_ERROR_KEY = 'clawjob_oauth_error'

function decodeParam(value: string | null): string {
  if (!value) return ''
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function parseOAuthFromUrl(search: string, hash: string): OAuthRedirectResult {
  const readError = (): string => {
    if (search) {
      const sp = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
      const qErr = sp.get('oauth_error') || sp.get('error')
      if (qErr) return decodeParam(qErr)
    }
    if (hash) {
      const q = hash.indexOf('?')
      if (q >= 0) {
        const e = new URLSearchParams(hash.slice(q + 1)).get('error')
        if (e) return decodeParam(e)
      }
    }
    if (search) {
      const e = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search).get('error')
      if (e) return decodeParam(e)
    }
    return ''
  }

  const error = readError()
  if (error) return { error }

  let token: string | null = null
  let username: string | null = null
  let userId: number | undefined

  const searchParams = search ? new URLSearchParams(search.startsWith('?') ? search.slice(1) : search) : null
  const fromGoogleQuery = searchParams?.get('from') === 'google'

  if (fromGoogleQuery && searchParams) {
    token = searchParams.get('token')
    username = searchParams.get('username')
    const uid = searchParams.get('user_id')
    userId = uid ? parseInt(uid, 10) : undefined
  } else if (hash.includes('/auth/callback')) {
    const q = hash.indexOf('?')
    const params = new URLSearchParams(q >= 0 ? hash.slice(q + 1) : '')
    token = params.get('token')
    username = params.get('username')
    const uid = params.get('user_id')
    userId = uid ? parseInt(uid, 10) : undefined
  }

  if (!token) return {}

  return {
    token,
    username: decodeParam(username),
    userId: userId != null && Number.isInteger(userId) ? userId : undefined,
  }
}

export function parseOAuthFromLocation(): OAuthRedirectResult {
  if (typeof window === 'undefined') return {}
  return parseOAuthFromUrl(window.location.search || '', window.location.hash || '')
}

/** After OAuth, strip sensitive params and land on a stable hash route. */
export function clearOAuthFromUrl(targetHash = '#/tasks'): void {
  if (typeof window === 'undefined') return
  const path = window.location.pathname || '/'
  const hash = targetHash.startsWith('#') ? targetHash : `#${targetHash}`
  window.history.replaceState(null, '', `${window.location.origin}${path}${hash}`)
}

export function stashOAuthError(error: string): void {
  try {
    sessionStorage.setItem(OAUTH_ERROR_KEY, error)
  } catch {
    /* ignore */
  }
}

export function takeStashedOAuthError(): string {
  try {
    const v = sessionStorage.getItem(OAUTH_ERROR_KEY) || ''
    if (v) sessionStorage.removeItem(OAUTH_ERROR_KEY)
    return v
  } catch {
    return ''
  }
}

export function hasOAuthRedirectParams(): boolean {
  const r = parseOAuthFromLocation()
  return !!(r.error || r.token)
}
