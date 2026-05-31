import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { getApiBase } from './api'

function mockLocation(protocol: string, hostname: string) {
  ;(globalThis as any).window = { location: { protocol, hostname } }
}

describe('getApiBase', () => {
  const prevWindow = (globalThis as any).window

  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', '')
  })

  afterEach(() => {
    ;(globalThis as any).window = prevWindow
    vi.unstubAllEnvs()
  })

  it('生产 IP 访问应使用 canonical api 域名而非 host:8000', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://8.216.64.80:8000')
    vi.stubEnv('VITE_SITE_DOMAIN', 'clawjob.com.cn')
    mockLocation('http:', '8.216.64.80')
    expect(getApiBase()).toBe('https://api.clawjob.com.cn')
  })

  it('本地 IP 开发（无 SITE_DOMAIN 覆盖）可退化为 host:8000', () => {
    vi.stubEnv('VITE_SITE_DOMAIN', '')
    vi.stubEnv('VITE_API_BASE_URL', '')
    mockLocation('http:', '127.0.0.1')
    expect(getApiBase()).toBe('http://localhost:8000')
  })

  it('域名访问 app.example.com 时改写为 api.example.com', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    mockLocation('https:', 'app.example.com')
    expect(getApiBase()).toBe('https://api.example.com')
  })

  it('域名访问 api.example.com 时使用当前 host', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    mockLocation('https:', 'api.example.com')
    expect(getApiBase()).toBe('https://api.example.com')
  })

  it('域名访问且 env 指向同域名时直接返回 env', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    mockLocation('https:', 'api.example.com')
    expect(getApiBase()).toBe('https://api.example.com')
  })
})
