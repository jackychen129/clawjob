/* NOTE: translated comment in English. */
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
