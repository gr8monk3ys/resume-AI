import { describe, it, expect, vi, beforeEach, afterEach, assert } from 'vitest'

import { authApi, ApiError } from '@/lib/api'

describe('authApi.deleteAccount', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    global.fetch = fetchMock
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends a DELETE request to /api/auth/account with the password and credentials', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'Account deleted successfully' }), { status: 200 })
    )

    await authApi.deleteAccount('correct-password')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const call = fetchMock.mock.calls.at(0)
    assert(call !== undefined)
    const [url, options] = call
    assert(options !== undefined)

    expect(url).toBe('http://localhost:8000/api/auth/account')
    expect(options.method).toBe('DELETE')
    expect(options.credentials).toBe('include')
    assert(typeof options.body === 'string')
    expect(JSON.parse(options.body)).toEqual({ password: 'correct-password' })
  })

  it('throws an ApiError when the password is incorrect', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Password is incorrect' }), { status: 400 })
    )

    await expect(authApi.deleteAccount('wrong-password')).rejects.toThrow(ApiError)
  })
})
