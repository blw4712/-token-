/**
 * 网页版技能上传：解析 SKILL.md 的 YAML frontmatter，保存在浏览器本地。
 * 不做任何落盘写入，也不会执行技能里的脚本。
 */
const STORAGE_KEY = 'agent-console:uploaded-skills'
const MAX_SIZE = 256 * 1024

export function loadUploaded() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function persistUploaded(items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {
    /* 隐私模式或配额不足时静默失败，页面仍显示本次会话数据 */
  }
}

function readValue(raw) {
  const text = String(raw ?? '').trim()
  if (text.startsWith('[') && text.endsWith(']')) {
    return text
      .slice(1, -1)
      .split(',')
      .map((item) => item.trim().replace(/^['"]|['"]$/g, ''))
      .filter(Boolean)
  }
  return text.replace(/^['"]|['"]$/g, '')
}

function readFrontmatter(lines) {
  const meta = {}
  let current = ''
  for (const line of lines) {
    const pair = line.match(/^([A-Za-z0-9_-]+)\s*:\s*(.*)$/)
    if (pair) {
      const [, key, value] = pair
      const text = value.trim()
      if (!text || /^[>|][+-]?$/.test(text)) {
        meta[key] = []
        current = key
      } else {
        meta[key] = readValue(text)
        current = ''
      }
      continue
    }
    const bullet = line.match(/^\s*-\s+(.*)$/)
    if (bullet && current) {
      meta[current].push(readValue(bullet[1]))
      continue
    }
    if (current && line.trim()) {
      meta[current].push(line.trim())
    }
  }
  return meta
}

function firstParagraph(body) {
  const blocks = body
    .split(/\n\s*\n/)
    .map((block) => block.replace(/^#+\s*/gm, '').trim())
    .filter(Boolean)
  return blocks[0] || ''
}

function asText(value) {
  if (Array.isArray(value)) return value.join(' ')
  return String(value || '')
}

export function parseSkillFile(text, fileName = '') {
  if (!text || !text.trim()) throw new Error('文件是空的')
  if (text.length > MAX_SIZE) throw new Error('文件超过 256KB，请确认是不是误传')

  const raw = text.replace(/\r\n/g, '\n')
  const lines = raw.split('\n')
  let meta = {}
  let body = raw

  if (lines[0]?.trim() === '---') {
    const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---')
    if (end > 0) {
      meta = readFrontmatter(lines.slice(1, end))
      body = lines.slice(end + 1).join('\n')
    }
  }

  const fallbackName = fileName.replace(/\.(md|markdown|txt)$/i, '')
  const name = (asText(meta.name) || fallbackName || 'untitled').trim()
  const description = (asText(meta.description) || firstParagraph(body) || '').trim()

  const tagText = asText(meta.tags || meta.keywords || '')
  const tags = tagText
    .split(/[,，\s]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 6)

  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name,
    description: description.length > 200 ? `${description.slice(0, 199)}…` : description,
    tags,
    file_name: fileName || `${name}.md`,
    size: text.length,
    added_at: new Date().toISOString(),
    content: raw
  }
}

export function downloadJson(items) {
  const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'my-skills.json'
  link.click()
  URL.revokeObjectURL(url)
}
