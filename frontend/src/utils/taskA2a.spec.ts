import { describe, it, expect } from 'vitest'
import { canA2aTaskParams } from './taskA2a'

describe('canA2aTaskParams', () => {
  it('未登录则不可', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: false,
        userId: 1,
        taskOwnerId: 2,
        taskAgentId: 5,
        myAgentIds: [5],
      }),
    ).toBe(false)
  })

  it('userId 为空则不可', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: null,
        taskOwnerId: 2,
        myAgentIds: [],
      }),
    ).toBe(false)
  })

  it('发布方可访问', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: 10,
        taskOwnerId: 10,
        taskAgentId: 7,
        myAgentIds: [],
      }),
    ).toBe(true)
  })

  it('接取方（名下 Agent 为 task.agent_id）可访问', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: 2,
        taskOwnerId: 99,
        taskAgentId: 7,
        myAgentIds: [7, 8],
      }),
    ).toBe(true)
  })

  it('非发布方且非接取 Agent 所属用户不可', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: 3,
        taskOwnerId: 99,
        taskAgentId: 7,
        myAgentIds: [8],
      }),
    ).toBe(false)
  })

  it('任务未分配 Agent 时仅发布方可访问', () => {
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: 2,
        taskOwnerId: 2,
        taskAgentId: null,
        myAgentIds: [],
      }),
    ).toBe(true)
    expect(
      canA2aTaskParams({
        isLoggedIn: true,
        userId: 3,
        taskOwnerId: 2,
        taskAgentId: null,
        myAgentIds: [9],
      }),
    ).toBe(false)
  })
})
