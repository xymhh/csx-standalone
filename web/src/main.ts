import { createApp } from 'vue'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'

import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import './styles/theme.css'

// 与改造前手写加载保持一致的语义：不自动重试、不在窗口聚焦时自动刷新、数据立即视为过期
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 0,
    },
  },
})

createApp(App).use(pinia).use(router).use(VueQueryPlugin, { queryClient }).mount('#app')
