<script setup lang="ts">
import { ref } from 'vue'

import Toast from '@/components/ui/Toast.vue'
import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'

const drawerOpen = ref(false)
const sidebarCompact = ref(false)
</script>

<template>
  <div class="min-h-dvh bg-bg text-fg">
    <Sidebar :open="drawerOpen" @close="drawerOpen = false" @compact-change="sidebarCompact = $event" />
    <div class="min-h-dvh transition-[padding] duration-200" :class="sidebarCompact ? 'lg:pl-20' : 'lg:pl-60'">
      <Topbar @menu="drawerOpen = true" />
      <main class="mx-auto w-full max-w-[1560px] px-4 pb-10 pt-6 sm:px-6 lg:px-8">
        <RouterView />
      </main>
    </div>
    <Toast />
  </div>
</template>
