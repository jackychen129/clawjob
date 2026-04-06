import { describe, it, expect } from 'vitest'
import { isTaskPulseHubRoute, taskPulseRelevantNav } from './taskPulseHub'

describe('isTaskPulseHubRoute', () => {
  it('首页与任务大厅为 Hub', () => {
    expect(isTaskPulseHubRoute('/')).toBe(true)
    expect(isTaskPulseHubRoute('/tasks')).toBe(true)
  })

  it('论坛与 inbox、dashboard、account 及其子路径为 Hub', () => {
    expect(isTaskPulseHubRoute('/forum')).toBe(true)
    expect(isTaskPulseHubRoute('/forum/thread/1')).toBe(true)
    expect(isTaskPulseHubRoute('/inbox')).toBe(true)
    expect(isTaskPulseHubRoute('/inbox/2')).toBe(true)
    expect(isTaskPulseHubRoute('/dashboard')).toBe(true)
    expect(isTaskPulseHubRoute('/dashboard/x')).toBe(true)
    expect(isTaskPulseHubRoute('/account')).toBe(true)
    expect(isTaskPulseHubRoute('/account/settings')).toBe(true)
  })

  it('其它业务页不是 Hub', () => {
    expect(isTaskPulseHubRoute('/marketplace')).toBe(false)
    expect(isTaskPulseHubRoute('/candidates')).toBe(false)
    expect(isTaskPulseHubRoute('/admin')).toBe(false)
    expect(isTaskPulseHubRoute('/tasks/123')).toBe(false)
  })
})

describe('taskPulseRelevantNav', () => {
  it('同路径不触发', () => {
    expect(taskPulseRelevantNav('/tasks', '/tasks')).toBe(false)
  })

  it('从 Hub 离开到非 Hub 仍触发（from 为 Hub）', () => {
    expect(taskPulseRelevantNav('/marketplace', '/tasks')).toBe(true)
  })

  it('进入 Hub 时触发（to 为 Hub）', () => {
    expect(taskPulseRelevantNav('/tasks', '/marketplace')).toBe(true)
  })

  it('两个非 Hub 之间不触发', () => {
    expect(taskPulseRelevantNav('/marketplace', '/candidates')).toBe(false)
  })
})
