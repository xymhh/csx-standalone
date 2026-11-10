import { createRouter, createWebHistory } from 'vue-router'

import { setUnauthorizedHandler } from '@/api/client'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('@/pages/DashboardPage.vue') },
        { path: 'discover', name: 'discover', component: () => import('@/pages/DiscoverPage.vue') },
        { path: 'progress', name: 'progress', component: () => import('@/pages/ProgressPage.vue') },
        { path: 'baseline', name: 'baseline', component: () => import('@/pages/BaselinePage.vue') },
        { path: 'radar', name: 'radar', component: () => import('@/pages/RadarPage.vue') },
        { path: 'candidates', name: 'candidates', component: () => import('@/pages/CandidatesPage.vue') },
        { path: 'tasks', name: 'tasks', component: () => import('@/pages/TasksPage.vue') },
        { path: 'history', name: 'history', component: () => import('@/pages/HistoryPage.vue') },
        { path: 'media', name: 'media', component: () => import('@/pages/MediaPage.vue') },
        { path: 'settings', name: 'settings', component: () => import('@/pages/SettingsPage.vue') },
        { path: 'search', name: 'search', component: () => import('@/pages/SearchPage.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  try {
    await useAuthStore(pinia).fetchMe()
    return true
  } catch {
    return { name: 'login', query: { next: to.fullPath } }
  }
})

// API 层遇到 401 时的统一处理：清登录态并跳登录页（替代原 CustomEvent 事件总线）
setUnauthorizedHandler(() => {
  useAuthStore(pinia).clear()
  if (router.currentRoute.value.name !== 'login') {
    void router.push({ name: 'login' })
  }
})

export default router
