<script setup lang="ts">
import { ref } from 'vue'
import { ChevronDown, Sliders } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import Switch from '@/components/ui/Switch.vue'

// 与 DramaSection 共享同一份 form（高级参数字段）
const form = defineModel<Record<string, any>>('form', { required: true })

// 高级参数折叠状态
const showAdvDrama = ref(false)
</script>

<template>
  <!-- 进阶高级参数折叠区 -->
  <div class="rounded-2xl border border-primary/[0.08] bg-canvas/40 overflow-hidden">
    <button
      type="button"
      class="flex w-full items-center justify-between p-4 text-left text-xs font-medium text-muted hover:text-fg transition-colors cursor-pointer"
      @click="showAdvDrama = !showAdvDrama"
    >
      <span class="flex items-center gap-2">
        <Sliders class="h-3.5 w-3.5" />
        <span>进阶追剧与中继参数（跨盘搬运、防假种、TMDB 密钥）</span>
      </span>
      <ChevronDown class="h-4 w-4 transition-transform" :class="showAdvDrama ? 'rotate-180' : ''" />
    </button>

    <div v-if="showAdvDrama" class="p-5 border-t border-primary/[0.06] space-y-4 text-xs">
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1.5">
          <label class="text-fg-2">防假种体积门槛 (MB)</label>
          <Input v-model.number="form.min_episode_size_mb" type="number" min="10" />
        </div>
        <div class="space-y-1.5">
          <label class="text-fg-2">更新搜索窗口 (天)</label>
          <Input v-model.number="form.window_days" type="number" min="1" />
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2 pt-2 border-t border-primary/[0.04]">
        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-fg">跳过特别篇 (S00)</p>
            <p class="text-[11px] text-subtle">不抓取预告、花絮与采访</p>
          </div>
          <Switch v-model="form.subscribe_skip_season_zero" />
        </div>
      </div>

      <div class="space-y-1.5 pt-2">
        <label class="text-fg-2">TMDB API 密钥 (用于补齐官方高清海报与演职员，留空使用内置密钥)</label>
        <Input v-model="form.tmdb_api_key" type="password" placeholder="留空使用系统预设密钥" />
      </div>
    </div>
  </div>
</template>
