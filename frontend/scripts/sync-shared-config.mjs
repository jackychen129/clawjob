#!/usr/bin/env node
/** 同步 shared/ 配置到 frontend 与 clawjob-website */
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = join(here, '..')
const repoRoot = join(frontendRoot, '..')
const sharedNav = join(repoRoot, 'shared/site-navigation.json')
const bundledNav = join(frontendRoot, 'src/config/site-navigation.json')

const source = existsSync(sharedNav) ? sharedNav : bundledNav

const targets = [
  join(frontendRoot, 'src/config/site-navigation.json'),
  join(repoRoot, '../clawjob-website/src/config/site-navigation.json'),
]

if (!existsSync(source)) {
  console.warn('[sync-shared-config] missing navigation json:', sharedNav, bundledNav)
  process.exit(0)
}

for (const dst of targets) {
  if (!existsSync(dirname(dst))) continue
  copyFileSync(source, dst)
  console.log('[sync-shared-config]', dst)
}
