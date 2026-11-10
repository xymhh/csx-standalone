import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api, setUnauthorizedHandler } from '@/api/client'

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api/client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    setUnauthorizedHandler(null)
  })

  it('成功 envelope 时解包 data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(200, { ok: true, data: { id: 7 }, error: null })),
    )
    await expect(api('/api/v1/anything')).resolves.toEqual({ id: 7 })
  })

  it('失败 envelope 时抛出带服务端消息的 ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(400, { ok: false, data: null, error: { code: 'BAD', message: '参数错误' } }),
      ),
    )
    const error = await api('/api/v1/anything').catch((cause: unknown) => cause)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(400)
    expect((error as ApiError).code).toBe('BAD')
    expect((error as ApiError).message).toBe('参数错误')
  })

  it('响应不是 envelope 时退化为 HTTP 状态错误', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('oops', { status: 500 })))
    const error = await api('/api/v1/anything').catch((cause: unknown) => cause)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(500)
    expect((error as ApiError).code).toBe('NETWORK')
  })

  it('401 时调用注册的未登录回调，但登录接口本身不触发', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(401, { ok: false, data: null, error: { code: 'AUTH', message: '未登录' } }),
      ),
    )
    await expect(api('/api/v1/auth/me')).rejects.toBeInstanceOf(ApiError)
    expect(handler).toHaveBeenCalledTimes(1)

    handler.mockClear()
    await expect(api('/api/v1/auth/login', { method: 'POST' })).rejects.toBeInstanceOf(ApiError)
    expect(handler).not.toHaveBeenCalled()
  })
})
