/**
 * 同一套页面支持两种数据源：
 * - live：Electron 面板 / 本地开发，请求 FastAPI
 * - static：GitHub Pages 构建（vite build --mode web），读取构建时导出的快照
 */
const STATIC_MODE = import.meta.env.MODE === 'web'
const SNAPSHOT_URL = `${import.meta.env.BASE_URL}data/snapshot.json`

let snapshotPromise = null

function loadSnapshot() {
  if (!snapshotPromise) {
    snapshotPromise = fetch(SNAPSHOT_URL).then((response) => {
      if (!response.ok) throw new Error(`快照读取失败（${response.status}）`)
      return response.json()
    })
  }
  return snapshotPromise
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = body.detail || ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `请求失败（${response.status}）`)
  }
  return response.json()
}

export const isStatic = STATIC_MODE

export async function getSnapshotInfo() {
  if (!STATIC_MODE) return null
  const data = await loadSnapshot()
  return {
    mode: data.mode,
    generated_at: data.generated_at,
    notice: data.notice
  }
}

export async function getOverview() {
  if (!STATIC_MODE) return request('/api/overview')
  const data = await loadSnapshot()
  return data.overview
}

export async function getDaily(days = 30) {
  if (!STATIC_MODE) return request(`/api/daily?days=${days}`)
  const data = await loadSnapshot()
  return { ...data.daily, days: data.daily.days.slice(-days) }
}

export async function getModels() {
  if (!STATIC_MODE) return request('/api/models')
  const data = await loadSnapshot()
  return data.models
}

export async function getSkills() {
  if (!STATIC_MODE) return request('/api/skills')
  const data = await loadSnapshot()
  return data.skills
}

export async function getMcp() {
  if (!STATIC_MODE) return request('/api/mcp')
  const data = await loadSnapshot()
  return data.mcp
}

export async function getAgents() {
  if (!STATIC_MODE) return request('/api/agents')
  const data = await loadSnapshot()
  return data.agents
}

export async function getPrices() {
  if (!STATIC_MODE) return request('/api/prices')
  const data = await loadSnapshot()
  return data.prices
}

export async function savePrices(payload) {
  if (STATIC_MODE) throw new Error('网页版是只读快照，请用桌面版修改单价')
  return request('/api/prices', { method: 'PUT', body: JSON.stringify(payload) })
}

export async function scan(full = false) {
  if (STATIC_MODE) throw new Error('网页版是只读快照，请用桌面版重新扫描')
  return request(`/api/scan?full=${full}`, { method: 'POST' })
}
