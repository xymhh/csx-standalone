<script setup lang="ts">
import { toastMessages } from '@/composables/useToast'
</script>
<template><div class="fixed bottom-4 right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite"><div v-for="item in toastMessages" :key="item.id" class="rounded-md border border-border bg-surface px-4 py-3 text-sm shadow-lg" :class="item.kind==='error'?'text-status-missing':item.kind==='success'?'text-status-ready':'text-fg'">{{item.message}}</div></div></template>