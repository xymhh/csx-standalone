<script setup lang="ts">
import { Tv } from '@lucide/vue'
import Switch from '@/components/ui/Switch.vue'

// 与 DramaSection 共享同一份 form（baseline 部分字段）
const form = defineModel<Record<string, any>>('form', { required: true })
</script>

<template>
  <!-- 卡片 A: 自动化追剧 -->
  <div class="apple-glass rounded-2xl p-5 space-y-4">
    <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
      <Tv class="h-4 w-4 text-blue-400" />
      <h3 class="text-sm font-semibold text-fg">自动追更调度</h3>
    </div>

    <div class="space-y-3.5 text-xs">
      <div class="flex items-center justify-between">
        <div>
          <p class="font-medium text-fg">自动化总开关</p>
          <p class="text-[11px] text-subtle">开启后定时轮询全网抓取追更</p>
        </div>
        <Switch v-model="form.enabled" />
      </div>

      <div class="flex items-center justify-between">
        <div>
          <p class="font-medium text-fg">片名智能订阅</p>
          <p class="text-[11px] text-subtle">频道抓取新剧自动加入追剧单</p>
        </div>
        <Switch v-model="form.title_subscribe_enabled" />
      </div>

      <div class="flex items-center justify-between">
        <div>
          <p class="font-medium text-fg">缺集全季补齐</p>
          <p class="text-[11px] text-subtle">追新集时同时回溯补全前面漏下的所有集</p>
        </div>
        <Switch v-model="form.subscribe_all_missing_seasons" />
      </div>
    </div>
  </div>
</template>
