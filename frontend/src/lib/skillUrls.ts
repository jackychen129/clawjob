/** 与 Skill 页一致的默认 Skill 仓库 ZIP 下载地址（用于发布到市场时一键填入）。 */
export function getDefaultSkillZipUrl(): string {
  const defaultRepo = 'https://github.com/jackychen129/clawjob-skill'
  const repo = (import.meta as unknown as { env?: { VITE_SKILL_REPO_URL?: string } }).env?.VITE_SKILL_REPO_URL || defaultRepo
  const base = String(repo).replace(/\/tree\/[^/]+/, '').replace(/\/$/, '')
  return `${base}/archive/refs/heads/main.zip`
}

export function getDefaultSkillRepoUrl(): string {
  const defaultRepo = 'https://github.com/jackychen129/clawjob-skill'
  return (import.meta as unknown as { env?: { VITE_SKILL_REPO_URL?: string } }).env?.VITE_SKILL_REPO_URL || defaultRepo
}
