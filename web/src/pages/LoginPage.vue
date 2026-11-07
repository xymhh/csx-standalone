<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import { ApiError, authApi } from '@/lib/api'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  if (loading.value) return
  loading.value = true
  error.value = null
  try {
    await authApi.login(username.value, password.value)
    const next = typeof route.query.next === 'string' ? route.query.next : '/'
    await router.replace(next)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="flex min-h-dvh items-center justify-center p-6">
    <form
      class="w-full max-w-sm space-y-5 rounded-card border border-border bg-surface p-7"
      @submit.prevent="submit"
    >
      <div class="space-y-1">
        <h1 class="text-xl font-semibold tracking-tight">CloudSubscribeX</h1>
        <p class="text-sm text-muted">登录以继续</p>
      </div>

      <div class="space-y-3">
        <label class="block space-y-1.5">
          <span class="text-xs text-muted">用户名</span>
          <Input v-model="username" autocomplete="username" placeholder="admin" />
        </label>
        <label class="block space-y-1.5">
          <span class="text-xs text-muted">密码</span>
          <Input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            :invalid="!!error"
          />
        </label>
      </div>

      <p v-if="error" class="text-sm text-status-missing">{{ error }}</p>

      <Button class="w-full" type="submit" :disabled="loading">
        {{ loading ? '登录中…' : '登录' }}
      </Button>
    </form>
  </main>
</template>
