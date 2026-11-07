<script setup lang="ts">
import { onMounted, ref } from 'vue'

import Button from '@/components/ui/Button.vue'
import { api } from '@/lib/api'

interface Meta {
  name: string
  version: string
}

const meta = ref<Meta | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    meta.value = await api<Meta>('/api/v1/meta')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <main class="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center gap-6 p-6">
    <h1 class="text-3xl font-semibold tracking-tight">CloudSubscribeX</h1>
    <p class="text-muted">独立版骨架已运行。后端：{{ meta?.version ?? '连接中…' }}</p>
    <p v-if="error" class="text-status-missing">{{ error }}</p>
    <div class="flex gap-3">
      <Button>开始</Button>
      <Button variant="outline">设置</Button>
    </div>
  </main>
</template>
