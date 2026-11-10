<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'

import Toast from '@/components/ui/Toast.vue'
import { useGlobalStore } from '@/stores/global'
import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'

const drawerOpen = ref(false)
const { sidebarCompact } = storeToRefs(useGlobalStore())
</script>

<template>
  <div class="min-h-dvh bg-bg text-fg">
    <Sidebar :open="drawerOpen" @close="drawerOpen = false" />
    <div class="min-h-dvh transition-[padding] duration-200" :class="sidebarCompact ? 'lg:pl-16' : 'lg:pl-64'">
      <Topbar @menu="drawerOpen = true" />
      <main class="mx-auto w-full max-w-[1400px] px-4 pb-12 pt-6 sm:px-6 lg:px-8">
        <RouterView />
      </main>
    </div>
    <Toast />
  </div>
</template>
