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

export const getOverview = () => request('/api/overview')
export const getDaily = (days = 30) => request(`/api/daily?days=${days}`)
export const getModels = () => request('/api/models')
export const getSkills = () => request('/api/skills')
export const getMcp = () => request('/api/mcp')
export const getAgents = () => request('/api/agents')
export const getPrices = () => request('/api/prices')
export const savePrices = (payload) =>
  request('/api/prices', { method: 'PUT', body: JSON.stringify(payload) })
export const scan = (full = false) =>
  request(`/api/scan?full=${full}`, { method: 'POST' })
