import { describe, it, expect } from 'vitest'
import { parseOAuthFromUrl } from './oauthCallback'

describe('parseOAuthFromUrl', () => {
  it('parses success params from hash callback', () => {
    const r = parseOAuthFromUrl('', '#/auth/callback?token=abc&username=alice&user_id=42')
    expect(r.token).toBe('abc')
    expect(r.username).toBe('alice')
    expect(r.userId).toBe(42)
  })

  it('parses legacy query callback', () => {
    const r = parseOAuthFromUrl('?from=google&token=tok&username=bob&user_id=7', '')
    expect(r.token).toBe('tok')
    expect(r.username).toBe('bob')
    expect(r.userId).toBe(7)
  })

  it('parses oauth_error from query', () => {
    const r = parseOAuthFromUrl('?oauth_error=token_exchange', '')
    expect(r.error).toBe('token_exchange')
  })

  it('parses error from hash', () => {
    const r = parseOAuthFromUrl('', '#/?error=token_exchange')
    expect(r.error).toBe('token_exchange')
  })
})
