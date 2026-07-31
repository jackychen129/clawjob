#!/usr/bin/env node
/**
 * 构建 clawjob-website 并复制到 frontend/public/home/
 * 供 LandingView iframe 加载，保留原版动效与视觉。
 */
import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(__dirname, '..')
const candidates = [
  path.resolve(frontendRoot, '../../clawjob-website'),
  path.resolve(frontendRoot, '../clawjob-website'),
]
const websiteRoot = candidates.find((p) => fs.existsSync(path.join(p, 'package.json')))
const outDir = path.join(frontendRoot, 'public', 'home')

if (!websiteRoot) {
  console.warn('[sync-website-home] 未找到 clawjob-website，跳过（使用已有 public/home）')
  process.exit(0)
}

const apiUrl = process.env.VITE_STATS_API_URL || process.env.VITE_API_BASE_URL || 'https://api.clawjob.com.cn'

console.log('[sync-website-home] building', websiteRoot)
execSync('node scripts/sync-shared-config.mjs', { cwd: frontendRoot, stdio: 'inherit' })
execSync('npm run build', {
  cwd: websiteRoot,
  stdio: 'inherit',
  env: {
    ...process.env,
    VITE_EMBEDDED_IN_APP: '1',
    VITE_STATS_API_URL: apiUrl,
  },
})

const dist = path.join(websiteRoot, 'dist')
if (!fs.existsSync(path.join(dist, 'index.html'))) {
  console.error('[sync-website-home] build 失败：dist/index.html 不存在')
  process.exit(1)
}

fs.rmSync(outDir, { recursive: true, force: true })
fs.cpSync(dist, outDir, { recursive: true })
console.log('[sync-website-home] → public/home/')
