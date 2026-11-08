<script setup lang="ts">
import { computed } from 'vue'
import { Clapperboard, Film, Sparkles } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import type { ProgressItem } from '@/lib/api'

const props = defineProps<{ media: ProgressItem }>()
defineEmits<{ select: [mediaId: number] }>()

// 根据片名哈希生成一个优雅的电影主题暗色渐变，避免无海报时的枯燥
const gradient = computed(() => {
  const gradients = [
    'from-blue-950/60 via-zinc-900 to-zinc-950',
    'from-emerald-950/60 via-zinc-900 to-zinc-950',
    'from-purple-950/60 via-zinc-900 to-zinc-950',
    'from-rose-950/60 via-zinc-900 to-zinc-950',
    'from-amber-950/60 via-zinc-900 to-zinc-950',
    'from-indigo-950/60 via-zinc-900 to-zinc-950',
  ]
  let sum = 0
  for (let i = 0; i < props.media.title.length; i++) {
    sum += props.media.title.charCodeAt(i)
  }
  return gradients[sum % gradients.length]
})

const percent = computed(() => {
  if (!props.media.aired_count) return 0
  return Math.min(100, Math.round((props.media.owned_count / props.media.aired_count) * 100))
})
</script>

<template>
  <article
    class="group relative flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-surface/80 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-zinc-700 hover:shadow-xl hover:shadow-black/50 cursor-pointer"
    @click="$emit('select', media.media_id)"
  >
    <!-- 顶部封面区域（2:3 电影海报风格比例，高质感） -->
    <div
      class="relative aspect-[16/10] w-full overflow-hidden bg-gradient-to-br transition-transform duration-300 group-hover:scale-105"
      :class="gradient"
    >
      <!-- 装饰水印图标 -->
      <div class="absolute inset-0 grid place-items-center opacity-25 transition-opacity group-hover:opacity-40">
        <Film class="h-12 w-12 text-zinc-100" />
      </div>

      <!-- 顶部浮层标签 -->
      <div class="absolute inset-x-3 top-3 flex items-center justify-between">
        <span class="rounded-md bg-black/60 px-2 py-0.5 text-[11px] font-medium text-zinc-300 backdrop-blur-md">
          {{ media.seasons.length > 1 ? `共 ${media.seasons.length} 季` : '第 1 季' }}
        </span>
        <Badge :tone="media.missing.length ? 'warn' : 'good'">
          {{ media.missing.length ? `缺 ${media.missing.length} 集` : '已齐' }}
        </Badge>
      </div>

      <!-- 底部暗影蒙版与片名 -->
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-zinc-950 via-zinc-950/80 to-transparent p-3 pt-8">
        <h3 class="truncate text-base font-semibold text-fg tracking-tight" :title="media.title">
          {{ media.title }}
        </h3>
      </div>
    </div>

    <!-- 底部进度信息 -->
    <div class="flex flex-1 flex-col justify-between p-3.5 pt-2">
      <div class="flex items-center justify-between text-xs text-subtle">
        <span>追更进度</span>
        <span class="font-mono font-medium tabular-nums text-fg">
          {{ media.owned_count }} <span class="text-subtle">/</span> {{ media.aired_count }} 集
        </span>
      </div>

      <!-- 进度条 -->
      <div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          class="h-full rounded-full transition-all duration-300"
          :class="media.missing.length ? 'bg-amber-400' : 'bg-status-ready'"
          :style="{ width: `${percent}%` }"
        />
      </div>

      <div class="mt-3 flex items-center justify-between text-[11px] text-subtle">
        <span>{{ percent === 100 ? '已全部入库' : `还差 ${media.missing.length} 集` }}</span>
        <span class="text-zinc-400 group-hover:text-fg transition-colors">查看季集明细 →</span>
      </div>
    </div>
  </article>
</template>
