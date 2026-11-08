<script setup lang="ts">
import { computed } from 'vue'
import { Film } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import type { ProgressItem } from '@/lib/api'

const props = defineProps<{ media: ProgressItem }>()
defineEmits<{ select: [mediaId: number] }>()

const gradient = computed(() => {
  const gradients = [
    'from-blue-950/80 via-zinc-950 to-black',
    'from-emerald-950/80 via-zinc-950 to-black',
    'from-purple-950/80 via-zinc-950 to-black',
    'from-rose-950/80 via-zinc-950 to-black',
    'from-amber-950/80 via-zinc-950 to-black',
    'from-indigo-950/80 via-zinc-950 to-black',
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
    class="group relative flex flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-zinc-900/60 shadow-md shadow-black/40 transition-all duration-200 hover:-translate-y-1 hover:border-zinc-700 hover:shadow-2xl hover:shadow-black/70 cursor-pointer"
    @click="$emit('select', media.media_id)"
  >
    <!-- 顶部封面区域（2:3 国际电影海报标准比例，大图主体优先） -->
    <div class="relative aspect-[2/3] w-full overflow-hidden bg-zinc-950">
      <!-- 真实 TMDB 官方高清海报 -->
      <img
        v-if="media.poster_url"
        :src="media.poster_url"
        :alt="media.title"
        loading="lazy"
        class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.025]"
      />

      <!-- 无海报时的深邃电影氛围渐变 -->
      <div
        v-else
        class="relative h-full w-full bg-gradient-to-br transition-transform duration-300 group-hover:scale-[1.025]"
        :class="gradient"
      >
        <div class="absolute inset-0 grid place-items-center opacity-25 transition-opacity group-hover:opacity-40">
          <Film class="h-12 w-12 text-zinc-100" />
        </div>
      </div>

      <!-- 顶部轻量浮层胶囊 -->
      <div class="absolute inset-x-2.5 top-2.5 flex items-center justify-between pointer-events-none">
        <span class="rounded-md bg-black/60 px-2 py-0.5 text-[10px] font-medium text-zinc-200 backdrop-blur-md border border-white/[0.06]">
          {{ media.seasons.length > 1 ? `共 ${media.seasons.length} 季` : '第 1 季' }}
        </span>
        <Badge :tone="media.missing.length ? 'warn' : 'good'">
          {{ media.missing.length ? `缺 ${media.missing.length} 集` : '已齐' }}
        </Badge>
      </div>

      <!-- 底部暗影自然过渡蒙版与标题 -->
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-zinc-950 via-zinc-950/80 to-transparent p-3 pt-12">
        <h3 class="truncate text-sm font-semibold text-white tracking-tight drop-shadow-sm" :title="media.title">
          {{ media.title }}
        </h3>
      </div>
    </div>

    <!-- 底部极简进度条信息 -->
    <div class="p-3 pt-2 space-y-2 bg-zinc-900/40">
      <div class="flex items-center justify-between text-[11px] text-zinc-400">
        <span>追更进度</span>
        <span class="font-mono font-medium tabular-nums text-zinc-200">
          {{ media.owned_count }} <span class="text-zinc-500">/</span> {{ media.aired_count }} 集
        </span>
      </div>

      <!-- 进度条 -->
      <div class="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          class="h-full rounded-full transition-all duration-300"
          :class="media.missing.length ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.3)]' : 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.3)]'"
          :style="{ width: `${percent}%` }"
        />
      </div>

      <div class="flex items-center justify-between text-[11px] text-zinc-500 pt-0.5">
        <span>{{ percent === 100 ? '全集已入库' : `还差 ${media.missing.length} 集` }}</span>
        <span class="text-zinc-400 group-hover:text-white transition-colors">展开季集 →</span>
      </div>
    </div>
  </article>
</template>
