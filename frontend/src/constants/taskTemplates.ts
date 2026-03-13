export interface TaskTemplate {
  id: string
  category: string
  description: string
  requirements: string
  skills_text: string
  location: string
  duration_estimate: string
}

const templates: TaskTemplate[] = [
  {
    id: 'none',
    category: '',
    description: '',
    requirements: '',
    skills_text: '',
    location: '',
    duration_estimate: '',
  },
  {
    id: 'research',
    category: 'research',
    description: '整理竞品或行业资料，输出结构化报告。',
    requirements: '输出 Markdown 或表格；包含来源与结论。',
    skills_text: '调研,文档',
    location: '',
    duration_estimate: '~2h',
  },
  {
    id: 'writing',
    category: 'writing',
    description: '技术文档、翻译或文案撰写。',
    requirements: '符合项目术语与格式要求。',
    skills_text: '写作,技术写作',
    location: '',
    duration_estimate: '~1h',
  },
  {
    id: 'development',
    category: 'development',
    description: '代码开发、脚本或自动化任务。',
    requirements: '可运行、带说明或测试。',
    skills_text: '代码,API',
    location: '',
    duration_estimate: '~3h',
  },
]

export function getTemplateById(id: string): TaskTemplate | undefined {
  return templates.find((t) => t.id === id)
}

export { templates }
