export const API_URL = import.meta.env.VITE_API_URL || ''

function apiUrl(path) {
  if (API_URL) return `${API_URL}${path}`
  return path
}

function wsUrl(path, token) {
  let base = API_URL
    ? API_URL.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  const sep = path.includes('?') ? '&' : '?'
  return `${base}${path}${sep}token=${encodeURIComponent(token)}`
}

export async function apiFetch(path, { method = 'GET', body, token } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(apiUrl(path), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    throw new Error('Session expired. Please log in again.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      /* ignore */
    }
    throw new Error(detail || 'Request failed')
  }
  if (res.status === 204) return null
  const contentType = res.headers.get('content-type') || ''
  return contentType.includes('application/json') ? res.json() : res.text()
}

export { apiUrl, wsUrl }
