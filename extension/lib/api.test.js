/**
 * Tests for the extension's shared lib (api.js, storage.js).
 * Run with `node --test lib/*.test.js` (or `bun run test`) from extension/ (no dependencies).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'

import { ApiClient, ApiError, toAutofillProfile, toJobCreate } from './api.js'
import { StorageHelper } from './storage.js'

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  }
}

function recordingFetch(routes) {
  const calls = []
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options })
    const key = `${options.method || 'GET'} ${new URL(url).pathname}`
    const handler = routes[key]
    if (!handler) return jsonResponse(404, { detail: `no route ${key}` })
    return handler(options)
  }
  return { calls, fetchImpl }
}

test('login posts an OAuth2 form and loads the current user', async () => {
  const { calls, fetchImpl } = recordingFetch({
    'POST /api/auth/login': () => jsonResponse(200, { access_token: 'tok', token_type: 'bearer' }),
    'GET /api/auth/me': () => jsonResponse(200, { id: 1, username: 'ada', email: 'a@x.io', full_name: 'Ada L' }),
  })
  const api = new ApiClient('http://localhost:8000/api/', fetchImpl)

  const result = await api.login('ada', 's3cret')

  assert.equal(calls[0].url, 'http://localhost:8000/api/auth/login')
  assert.equal(calls[0].options.headers['Content-Type'], 'application/x-www-form-urlencoded')
  assert.equal(calls[0].options.body, 'username=ada&password=s3cret')
  assert.equal(calls[0].options.credentials, 'include')
  assert.equal(calls[1].options.headers.Authorization, 'Bearer tok')
  assert.deepEqual(result, {
    access_token: 'tok',
    refresh_token: null,
    user: { id: 1, username: 'ada', email: 'a@x.io', full_name: 'Ada L', name: 'Ada L' },
  })
})

test('failed login surfaces the backend detail as an ApiError', async () => {
  const { fetchImpl } = recordingFetch({
    'POST /api/auth/login': () => jsonResponse(401, { detail: 'Incorrect username or password' }),
  })
  const api = new ApiClient(undefined, fetchImpl)

  await assert.rejects(api.login('ada', 'bad'), (err) => {
    assert.ok(err instanceof ApiError)
    assert.equal(err.status, 401)
    assert.equal(err.message, 'Incorrect username or password')
    return true
  })
})

test('validation errors are joined into one message', async () => {
  const { fetchImpl } = recordingFetch({
    'POST /api/jobs': () => jsonResponse(422, { detail: [{ msg: 'field required' }, { msg: 'bad enum' }] }),
  })
  const api = new ApiClient(undefined, fetchImpl)
  await assert.rejects(api.createJobApplication('tok', { title: 't', company: 'c' }), /field required; bad enum/)
})

test('network failure becomes an ApiError with status 0', async () => {
  const api = new ApiClient(undefined, async () => {
    throw new TypeError('Failed to fetch')
  })
  await assert.rejects(api.getProfile('tok'), (err) => err instanceof ApiError && err.status === 0)
})

test('authenticated calls without a token fail before any request', async () => {
  const { calls, fetchImpl } = recordingFetch({})
  const api = new ApiClient(undefined, fetchImpl)
  await assert.rejects(api.getProfile(undefined), /Not authenticated/)
  assert.equal(calls.length, 0)
})

test('refreshToken sends the token in the body and keeps it when none is returned', async () => {
  const { calls, fetchImpl } = recordingFetch({
    'POST /api/auth/refresh': () => jsonResponse(200, { access_token: 'new', token_type: 'bearer' }),
  })
  const api = new ApiClient(undefined, fetchImpl)

  const result = await api.refreshToken('r1')

  assert.equal(calls[0].options.body, JSON.stringify({ refresh_token: 'r1' }))
  assert.deepEqual(result, { access_token: 'new', refresh_token: 'r1' })
})

test('getProfile shapes the backend profile for the fillers', async () => {
  const { fetchImpl } = recordingFetch({
    'GET /api/profile': () =>
      jsonResponse(200, {
        id: 3,
        name: 'Grace Brewster Hopper',
        email: 'g@navy.mil',
        phone: null,
        linkedin: 'https://linkedin.com/in/grace',
        github: null,
        portfolio: 'https://grace.dev',
      }),
  })
  const profile = await new ApiClient(undefined, fetchImpl).getProfile('tok')

  assert.equal(profile.firstName, 'Grace')
  assert.equal(profile.lastName, 'Brewster Hopper')
  assert.equal(profile.linkedIn, 'https://linkedin.com/in/grace')
  assert.equal(profile.website, 'https://grace.dev')
  assert.equal(profile.phone, '')
  assert.equal(profile.id, 3)
})

test('toAutofillProfile tolerates a single-word or empty name', () => {
  assert.equal(toAutofillProfile({ name: 'Cher' }).lastName, '')
  assert.equal(toAutofillProfile({ name: '' }).firstName, '')
})

test('createJobApplication maps the extension job shape to JobCreate', async () => {
  const { calls, fetchImpl } = recordingFetch({
    'POST /api/jobs': (options) => jsonResponse(201, { id: 9, ...JSON.parse(options.body) }),
  })
  const api = new ApiClient(undefined, fetchImpl)

  const created = await api.createJobApplication('tok', {
    title: 'Engineer',
    company: 'Acme',
    location: 'Remote',
    url: 'https://jobs.lever.co/acme/1',
    description: 'Build things',
    status: 'Bookmarked',
    source: 'linkedin',
  })

  assert.equal(calls[0].options.headers.Authorization, 'Bearer tok')
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    company: 'Acme',
    position: 'Engineer',
    status: 'Bookmarked',
    location: 'Remote',
    job_url: 'https://jobs.lever.co/acme/1',
    job_description: 'Build things',
    application_source: 'LinkedIn',
  })
  assert.equal(created.id, 9)
})

test('toJobCreate falls back for unknown sources and missing fields', () => {
  assert.deepEqual(toJobCreate({ source: 'greenhouse' }), {
    company: 'Unknown company',
    position: 'Unknown position',
    status: 'Bookmarked',
    application_source: 'Other',
  })
  assert.equal(toJobCreate({ title: 'x', company: 'y' }).application_source, undefined)
})

test('StorageHelper wraps a chrome.storage area', async () => {
  const data = {}
  const area = {
    async get(keys) {
      if (keys === null) return { ...data }
      const list = Array.isArray(keys) ? keys : [keys]
      return Object.fromEntries(list.filter((k) => k in data).map((k) => [k, data[k]]))
    },
    async set(items) {
      Object.assign(data, items)
    },
    async remove(keys) {
      for (const k of Array.isArray(keys) ? keys : [keys]) delete data[k]
    },
    async clear() {
      for (const k of Object.keys(data)) delete data[k]
    },
  }
  const storage = new StorageHelper(area)

  await storage.set({ accessToken: 'tok', user: { id: 1 } })
  assert.deepEqual(await storage.get('accessToken'), { accessToken: 'tok' })
  assert.deepEqual(await storage.get(['accessToken', 'missing']), { accessToken: 'tok' })
  await storage.remove(['accessToken'])
  assert.deepEqual(await storage.get(null), { user: { id: 1 } })
  await storage.clear()
  assert.deepEqual(await storage.get(null), {})
})

test('StorageHelper defaults to chrome.storage.local', () => {
  const local = { get() {}, set() {}, remove() {}, clear() {} }
  globalThis.chrome = { storage: { local } }
  try {
    assert.equal(new StorageHelper().area, local)
  } finally {
    delete globalThis.chrome
  }
  assert.throws(() => new StorageHelper(), /chrome.storage is not available/)
})
