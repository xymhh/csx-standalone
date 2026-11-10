import { api } from './client'

export interface Me {
  username: string
}

export const authApi = {
  login: (username: string, password: string) =>
    api<Me>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => api<null>('/api/v1/auth/logout', { method: 'POST' }),
  me: () => api<Me>('/api/v1/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    api<{ changed: boolean }>('/api/v1/auth/password', {
      method: 'POST',
      body: JSON.stringify({ old_password, new_password }),
    }),
}
