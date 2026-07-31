import { describe, expect, it } from 'vitest'
import { canonicalAppUrl, canonicalSkillDocsUrl, canonicalWwwUrl } from './siteUrls'

describe('siteUrls', () => {
  it('canonicalWwwUrl uses hash routes', () => {
    expect(canonicalWwwUrl('/')).toBe('https://clawjob.com.cn/#/')
    expect(canonicalWwwUrl('/tasks')).toBe('https://clawjob.com.cn/#/tasks')
  })

  it('canonicalAppUrl matches www hash routes', () => {
    expect(canonicalAppUrl('/tasks')).toBe('https://clawjob.com.cn/#/tasks')
    expect(canonicalAppUrl()).toBe('https://clawjob.com.cn/#/tasks')
  })

  it('canonicalSkillDocsUrl has no trailing slash', () => {
    expect(canonicalSkillDocsUrl()).toBe('https://clawjob.com.cn/#/skill')
  })
})
