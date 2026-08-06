import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { authApi, ApiError } from '@/lib/api'

describe('authApi.deleteAccount', () => {
  const fetchMock = vi.fn()

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
    const call = fetchMock.mock.calls[0] as [string, RequestInit]
    const [url, options] = call

    expect(url).toBe('http://localhost:8000/api/auth/account')
    expect(options.method).toBe('DELETE')
    expect(options.credentials).toBe('include')
    expect(JSON.parse(options.body as string)).toEqual({ password: 'correct-password' })
  })

  it('throws an ApiError when the password is incorrect', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Password is incorrect' }), { status: 400 })
    )

    await expect(authApi.deleteAccount('wrong-password')).rejects.toThrow(ApiError)
  })
})
