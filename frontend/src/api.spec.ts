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

  it('回归：IP 访问 + env 指向同一 IP，应直接返回 env，绝不拼成 api.<ip>', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://8.216.64.80:8000')
    mockLocation('http:', '8.216.64.80')
    expect(getApiBase()).toBe('http://8.216.64.80:8000')
  })

  it('回归：IP 访问且 env 为 localhost 时，应退化为 host:8000', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    mockLocation('http:', '8.216.64.80')
    expect(getApiBase()).toBe('http://8.216.64.80:8000')
  })

  it('回归：IP 访问且未配置 env，退化为 host:8000', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    mockLocation('http:', '8.216.64.80')
    expect(getApiBase()).toBe('http://8.216.64.80:8000')
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
