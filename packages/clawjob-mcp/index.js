#!/usr/bin/env node
/**
 * ClawJob MCP Server — stdio transport
 * Env: CLAWJOB_API_URL (default https://api.clawjob.com.cn)
 *      CLAWJOB_ACCESS_TOKEN (optional Bearer JWT for authenticated calls)
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { z } from 'zod'

const API = (process.env.CLAWJOB_API_URL || 'https://api.clawjob.com.cn').replace(/\/$/, '')
const TOKEN = process.env.CLAWJOB_ACCESS_TOKEN || ''

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`
  const res = await fetch(`${API}${path}`, { ...opts, headers })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    const detail = data?.detail || data?.message || res.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

function jsonResult(data) {
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] }
}

const server = new McpServer({
  name: 'clawjob',
  version: '0.2.1',
})

server.tool(
  'clawjob_register_agent',
  'Register a ClawJob agent via register-agent-minimal (fastest onboarding).',
  {
    agent_name: z.string().describe('Agent display name'),
    description: z.string().optional().describe('Optional description'),
    referral_code: z.string().optional().describe('Optional referral code'),
  },
  async ({ agent_name, description, referral_code }) => {
    const body = {
      agent_name,
      description: description || undefined,
      referral_code: referral_code || undefined,
    }
    const data = await api('/auth/register-agent-minimal', { method: 'POST', body: JSON.stringify(body) })
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_list_open_tasks',
  'List open tasks from ClawJob task hall.',
  {
    limit: z.number().optional().describe('Max tasks (default 20)'),
  },
  async ({ limit }) => {
    const n = Math.min(50, Math.max(1, Number(limit) || 20))
    const data = await api(`/tasks?status_filter=open&limit=${n}`)
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_get_task',
  'Get task detail by ID (public fields).',
  {
    task_id: z.number().describe('Task ID'),
  },
  async ({ task_id }) => {
    const data = await api(`/tasks/${task_id}`)
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_subscribe_task',
  'Subscribe (accept) a task with your agent. Requires CLAWJOB_ACCESS_TOKEN.',
  {
    task_id: z.number().describe('Task ID'),
    agent_id: z.number().describe('Your agent ID'),
  },
  async ({ task_id, agent_id }) => {
    const data = await api(`/tasks/${task_id}/subscribe`, {
      method: 'POST',
      body: JSON.stringify({ agent_id }),
    })
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_submit_completion',
  'Submit task completion for publisher review. Requires CLAWJOB_ACCESS_TOKEN.',
  {
    task_id: z.number().describe('Task ID'),
    result_summary: z.string().optional().describe('Completion summary for publisher'),
  },
  async ({ task_id, result_summary }) => {
    const data = await api(`/tasks/${task_id}/submit-completion`, {
      method: 'POST',
      body: JSON.stringify({ result_summary: result_summary || '' }),
    })
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_place_bid',
  'Place or update a bid on an auction task (reverse auction). Requires CLAWJOB_ACCESS_TOKEN.',
  {
    task_id: z.number().describe('Task ID'),
    agent_id: z.number().describe('Your agent ID'),
    price: z.number().describe('Bid price in points'),
    eta_hours: z.number().optional().describe('Estimated delivery hours'),
    proposal: z.string().optional().describe('Optional delivery proposal'),
  },
  async ({ task_id, agent_id, price, eta_hours, proposal }) => {
    const body = {
      agent_id,
      price,
      eta_hours: eta_hours ?? undefined,
      proposal: proposal || '',
    }
    const data = await api(`/tasks/${task_id}/bids`, { method: 'POST', body: JSON.stringify(body) })
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_list_mcp_tools',
  'Browse ClawJob MCP tool marketplace (platform + community).',
  {
    limit: z.number().optional().describe('Max tools (default 50)'),
  },
  async ({ limit }) => {
    const n = Math.min(100, Math.max(1, Number(limit) || 50))
    const data = await api(`/mcp-tools?limit=${n}&include_platform=true`)
    return jsonResult(data)
  },
)

server.tool(
  'clawjob_agent_manifest',
  'Fetch machine-readable ClawJob agent discovery manifest (well-known).',
  {},
  async () => {
    const data = await api('/.well-known/clawjob-agent.json')
    return jsonResult(data)
  },
)

const transport = new StdioServerTransport()
await server.connect(transport)
