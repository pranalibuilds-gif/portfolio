import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

const stored = new Map()
const events = []
const originalFetch = globalThis.fetch

Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: {
    getItem: (key) => stored.get(key) ?? null,
    setItem: (key, value) => stored.set(key, String(value)),
    removeItem: (key) => stored.delete(key),
  },
})
Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: {
    dispatchEvent: (event) => events.push(event.type),
  },
})

const { ApiError, apiRequest, collectionUrl, itemPath, login, resultCount, tokenStore } =
  await import('../src/api.js')

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  tokenStore.clear()
  stored.clear()
  events.length = 0
  globalThis.fetch = originalFetch
})

test('token store writes and clears session-scoped tokens', () => {
  tokenStore.set({ access: 'access-token', refresh: 'refresh-token' })
  assert.equal(tokenStore.access, 'access-token')
  assert.equal(tokenStore.refresh, 'refresh-token')

  tokenStore.clear()
  assert.equal(tokenStore.access, null)
  assert.equal(tokenStore.refresh, null)
})

test('login stores the token pair and sends JSON credentials', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://127.0.0.1:8000/api/auth/token/')
    assert.equal(options.headers['Content-Type'], 'application/json')
    assert.deepEqual(JSON.parse(options.body), { username: 'staff', password: 'secret' })
    return jsonResponse({ access: 'access-token', refresh: 'refresh-token' })
  }

  await login('staff', 'secret')
  assert.equal(tokenStore.access, 'access-token')
  assert.equal(tokenStore.refresh, 'refresh-token')
})

test('API requests include bearer auth and return JSON or null for 204', async () => {
  tokenStore.set({ access: 'access-token', refresh: 'refresh-token' })
  const received = []
  globalThis.fetch = async (url, options) => {
    received.push({ url, authorization: options.headers.get('Authorization') })
    return received.length === 1 ? jsonResponse({ count: 1 }) : new Response(null, { status: 204 })
  }

  assert.deepEqual(await apiRequest('/cms/projects/'), { count: 1 })
  assert.equal(await apiRequest('/cms/projects/1/'), null)
  assert.deepEqual(received, [
    { url: 'http://127.0.0.1:8000/api/cms/projects/', authorization: 'Bearer access-token' },
    { url: 'http://127.0.0.1:8000/api/cms/projects/1/', authorization: 'Bearer access-token' },
  ])
})

test('expired access token refreshes once and retries the original request', async () => {
  tokenStore.set({ access: 'expired-access', refresh: 'valid-refresh' })
  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push({ url, authorization: options.headers?.get?.('Authorization') })
    if (url.endsWith('/auth/token/refresh/')) {
      return jsonResponse({ access: 'renewed-access' })
    }
    if (calls.filter((call) => call.url.endsWith('/cms/projects/')).length === 1) {
      return jsonResponse({ detail: 'expired' }, 401)
    }
    return jsonResponse({ results: [] })
  }

  assert.deepEqual(await apiRequest('/cms/projects/'), { results: [] })
  assert.equal(tokenStore.access, 'renewed-access')
  assert.equal(calls.length, 3)
  assert.equal(calls[0].authorization, 'Bearer expired-access')
  assert.equal(calls[2].authorization, 'Bearer renewed-access')
})

test('rejected refresh clears tokens, emits expiry, and surfaces ApiError', async () => {
  tokenStore.set({ access: 'expired-access', refresh: 'expired-refresh' })
  globalThis.fetch = async (url) => (
    url.endsWith('/auth/token/refresh/')
      ? jsonResponse({ detail: 'invalid refresh' }, 401)
      : jsonResponse({ detail: 'expired access' }, 401)
  )

  await assert.rejects(
    apiRequest('/cms/projects/'),
    (error) => error instanceof ApiError && error.status === 401,
  )
  assert.equal(tokenStore.access, null)
  assert.equal(tokenStore.refresh, null)
  assert.deepEqual(events, ['cms-auth-expired'])
})

test('HTTP and network failures produce useful API errors', async () => {
  globalThis.fetch = async () => jsonResponse({ detail: 'Not allowed.' }, 403)
  await assert.rejects(
    apiRequest('/cms/projects/'),
    (error) => error instanceof ApiError && error.status === 403 && error.message === 'Not allowed.',
  )

  globalThis.fetch = async () => { throw new Error('offline') }
  await assert.rejects(
    apiRequest('/public/projects/'),
    (error) => error instanceof ApiError && error.status === 0 && error.message.includes('Could not reach the API'),
  )
})

test('collection helpers encode query values and count paginated results', () => {
  assert.equal(
    collectionUrl('projects', { page: 2, search: 'design & code', status: '' }),
    '/cms/projects/?page=2&search=design+%26+code',
  )
  assert.equal(itemPath('projects', 7, 'publish'), '/cms/projects/7/publish/')
  assert.equal(itemPath('projects', 7), '/cms/projects/7/')
  assert.equal(resultCount({ count: 12, results: [] }), 12)
  assert.equal(resultCount([1, 2]), 2)
  assert.equal(resultCount(null), 0)
})
