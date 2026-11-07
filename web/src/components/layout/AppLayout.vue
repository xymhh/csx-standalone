<script setup lang="ts">
import { ref } from 'vue';import Sidebar from './Sidebar.vue';import Topbar from './Topbar.vue';import Toast from '@/components/ui/Toast.vue';const open=ref(false)
</script>
<template><div class="min-h-dvh bg-bg text-fg"><Sidebar :open="open" @close="open=false"/><div class="min-h-dvh transition-all lg:pl-60"><Topbar @menu="open=true"/><main class="mx-auto w-full max-w-[1500px] p-4 pb-8 sm:p-6"><RouterView/></main></div><Toast/></div></template>