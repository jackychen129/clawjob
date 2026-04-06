import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * Render user-authored Markdown to sanitized HTML for v-html.
 * Use only with trusted workflow: parse → DOMPurify.sanitize.
 */
export function renderMarkdownToSafeHtml(src: string): string {
  if (!src || !String(src).trim()) return ''
  const raw = marked.parse(String(src), { async: false }) as string
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
  })
}
