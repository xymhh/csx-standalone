import { createRouter, createWebHistory } from 'vue-router'

import { authApi } from '@/lib/api'

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
    await authApi.me()
    return true
  } catch {
    return { name: 'login', query: { next: to.fullPath } }
  }
})

window.addEventListener('csx:unauthorized', () => {
  if (router.currentRoute.value.name !== 'login') {
    void router.push({ name: 'login' })
  }
})

export default router
