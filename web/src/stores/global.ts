import { defineStore } from 'pinia'
import { ref } from 'vue'

// 全局 UI 状态：目前承载侧边栏收起状态（原先由 Sidebar 本地 ref + emit 传递）
export const useGlobalStore = defineStore('global', () => {
  const sidebarCompact = ref(false)

  function toggleSidebarCompact() {
    sidebarCompact.value = !sidebarCompact.value
  }

  return { sidebarCompact, toggleSidebarCompact }
})
