import { createPinia } from 'pinia'

// 全局共享的 pinia 实例：main.ts 安装、router 守卫显式引用，避免依赖「激活实例」的隐式时序
export const pinia = createPinia()
