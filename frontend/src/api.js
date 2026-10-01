const API_BASE = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')
const ACCESS_KEY = 'cms.access'
const REFRESH_KEY = 'cms.refresh'

let refreshRequest

export const tokenStore = {
  get access() {
    return sessionStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return sessionStorage.getItem(REFRESH_KEY)
  },
  set(tokens) {
    sessionStorage.setItem(ACCESS_KEY, tokens.access)
    if (tokens.refresh) sessionStorage.setItem(REFRESH_KEY, tokens.refresh)
  },
  clear() {
    sessionStorage.removeItem(ACCESS_KEY)
    sessionStorage.removeItem(REFRESH_KEY)
  },
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

function messageFrom(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (data.non_field_errors) return data.non_field_errors.join(' ')
  return fallback
}

async function readResponse(response) {
  if (response.status === 204) return null
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) return response.json()
  const text = await response.text()
  return text || null
}

async function refreshAccess() {
  if (refreshRequest) return refreshRequest
  const refresh = tokenStore.refresh
  if (!refresh) {
    tokenStore.clear()
    return false
  }
  refreshRequest = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      const data = await readResponse(response)
      if (!response.ok || !data?.access) throw new Error('Refresh rejected')
      tokenStore.set(data)
      return true
    } catch {
      tokenStore.clear()
      return false
    } finally {
      refreshRequest = undefined
    }
  })()
  return refreshRequest
}

export async function apiRequest(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {})
  if (tokenStore.access) headers.set('Authorization', `Bearer ${tokenStore.access}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError('Could not reach the API. Check that the backend is running and the API URL is correct.', 0)
  }
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await refreshAccess()) return apiRequest(path, options, false)
  }
  const data = await readResponse(response)
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('cms-auth-expired'))
    throw new ApiError(messageFrom(data, `Request failed (${response.status}).`), response.status, data)
  }
  return data
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }).catch(() => {
    throw new ApiError('Could not reach the API. Check that the backend is running and the API URL is correct.', 0)
  })
  const data = await readResponse(response)
  if (!response.ok) throw new ApiError(messageFrom(data, 'Sign in failed.'), response.status, data)
  tokenStore.set(data)
  return data
}

export function collectionUrl(resource, params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const suffix = query.toString()
  return `/cms/${resource}/${suffix ? `?${suffix}` : ''}`
}

export function itemPath(resource, id, action = '') {
  return `/cms/${resource}/${id}/${action ? `${action}/` : ''}`
}

export function resultCount(data) {
  return Array.isArray(data) ? data.length : data?.count ?? 0
}
