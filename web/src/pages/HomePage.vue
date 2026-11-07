<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import Button from '@/components/ui/Button.vue'
import { api, authApi } from '@/lib/api'

interface Meta {
  name: string
  version: string
}

const router = useRouter()
const meta = ref<Meta | null>(null)
const username = ref('')

onMounted(async () => {
  meta.value = await api<Meta>('/api/v1/meta')
  username.value = (await authApi.me()).username
})

async function logout() {
  await authApi.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <main class="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center gap-6 p-6">
    <div class="flex items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-3xl font-semibold tracking-tight">CloudSubscribeX</h1>
        <p class="text-sm text-muted">
          后端 {{ meta?.version ?? '连接中…' }} · 登录为 {{ username || '…' }}
        </p>
      </div>
      <Button variant="outline" size="sm" @click="logout">退出</Button>
    </div>

    <div class="rounded-card border border-border bg-surface p-5 text-sm text-muted">
      P0 骨架运行中。领域模型与业务页面将在 P1 / P5 落地。
    </div>
  </main>
</template>
