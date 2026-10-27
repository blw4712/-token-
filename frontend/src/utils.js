export function tokens(value) {
  const number = Number(value || 0)
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(2)}M`
  if (number >= 1_000) return `${(number / 1_000).toFixed(1)}k`
  return String(number)
}

export function money(value, digits = 2) {
  if (value === null || value === undefined) return '—'
  return `¥${Number(value).toFixed(digits)}`
}

export function percent(value, total) {
  if (!total) return '0%'
  return `${((value / total) * 100).toFixed(1)}%`
}

export function shortDate(day) {
  return day ? day.slice(5) : ''
}

export function timeText(value) {
  if (!value) return '尚未扫描'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}
