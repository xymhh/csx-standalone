import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/api/auth', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
  },
}))

import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const meMock = vi.mocked(authApi.me)
const loginMock = vi.mocked(authApi.login)
const logoutMock = vi.mocked(authApi.logout)

describe('stores/auth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchMe 成功后写入当前用户', async () => {
    meMock.mockResolvedValue({ username: 'ben' })
    const store = useAuthStore()
    await expect(store.fetchMe()).resolves.toEqual({ username: 'ben' })
    expect(store.user).toEqual({ username: 'ben' })
  })

  it('fetchMe 失败时向上抛错且不写入用户（路由守卫据此跳登录）', async () => {
    meMock.mockRejectedValue(new Error('未登录'))
    const store = useAuthStore()
    await expect(store.fetchMe()).rejects.toThrow('未登录')
    expect(store.user).toBeNull()
  })

  it('login 成功后写入用户，logout 后清空（接口失败也清空）', async () => {
    loginMock.mockResolvedValue({ username: 'ben' })
    const store = useAuthStore()
    await store.login('ben', 'secret')
    expect(store.user).toEqual({ username: 'ben' })

    logoutMock.mockRejectedValue(new Error('网络错误'))
    await expect(store.logout()).rejects.toThrow('网络错误')
    expect(store.user).toBeNull()
  })

  it('clear 立即清空用户（401 回调走这条路径）', async () => {
    loginMock.mockResolvedValue({ username: 'ben' })
    const store = useAuthStore()
    await store.login('ben', 'secret')
    store.clear()
    expect(store.user).toBeNull()
  })
})
