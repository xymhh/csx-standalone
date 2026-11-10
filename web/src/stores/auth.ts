import { defineStore } from 'pinia'
import { ref } from 'vue'

import { authApi, type Me } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<Me | null>(null)

  // 拉取当前登录用户：成功写入 store，失败抛出给调用方（路由守卫据此跳登录）
  async function fetchMe(): Promise<Me> {
    const me = await authApi.me()
    user.value = me
    return me
  }

  async function login(username: string, password: string): Promise<Me> {
    const me = await authApi.login(username, password)
    user.value = me
    return me
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  function clear() {
    user.value = null
  }

  return { user, fetchMe, login, logout, clear }
})
