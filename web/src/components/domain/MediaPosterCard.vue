<script setup lang="ts">
import { computed, useSlots } from 'vue'
import { Film } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import { posterSrc } from '@/lib/poster'
import type { ProgressItem } from '@/api/subscriptions'

const props = defineProps<{ media: ProgressItem }>()
defineEmits<{ select: [mediaId: number] }>()
const slots = useSlots()

const gradient = computed(() => {
  const gradients = [
    'from-blue-950/70 via-canvas to-bg',
    'from-emerald-950/70 via-canvas to-bg',
    'from-purple-950/70 via-canvas to-bg',
    'from-rose-950/70 via-canvas to-bg',
    'from-amber-950/70 via-canvas to-bg',
    'from-indigo-950/70 via-canvas to-bg',
  ]
  let sum = 0
  for (let i = 0; i < props.media.title.length; i++) {
    sum += props.media.title.charCodeAt(i)
  }
  return gradients[sum % gradients.length]
})

const paused = computed(() => props.media.subscription_state === 'paused')

const percent = computed(() => {
  if (!props.media.aired_count) return 0
  return Math.min(100, Math.round((props.media.owned_count / props.media.aired_count) * 100))
})
</script>

<template>
  <article
    class="apple-glass apple-glass-hover group relative flex flex-col overflow-hidden rounded-2xl cursor-pointer"
    @click="$emit('select', media.media_id)"
  >
    <!-- 顶部封面区域（2:3 国际标准纵横比，大图全幅呈现） -->
    <div class="relative aspect-[2/3] w-full overflow-hidden bg-canvas">
      <!-- 官方高清海报 -->
      <img
        v-if="media.poster_url"
        :src="posterSrc(media.poster_url)"
        :alt="media.title"
        loading="lazy"
        class="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
        :class="paused ? 'grayscale' : ''"
      />

      <!-- 无海报时的微质感电影暗夜渐变 -->
      <div
        v-else
        class="relative h-full w-full bg-gradient-to-br transition-transform duration-500 ease-out group-hover:scale-105"
        :class="gradient"
      >
        <div class="absolute inset-0 grid place-items-center opacity-25 transition-opacity group-hover:opacity-40">
          <Film class="h-12 w-12 text-fg" />
        </div>
      </div>

      <!-- 暂停态灰度遮罩 -->
      <div v-if="paused" class="pointer-events-none absolute inset-0 bg-bg/40" />

      <!-- 顶部半透明轻盈胶囊 -->
      <div class="absolute inset-x-2.5 top-2.5 flex items-center justify-between pointer-events-none" :class="slots.actions ? 'pr-9' : ''">
        <span
          class="rounded-full px-2.5 py-0.5 text-[10px] font-medium backdrop-blur-xl border shadow-sm"
          :class="paused ? 'border-amber-500/30 bg-amber-500/15 text-amber-300' : 'border-primary/10 bg-bg/60 text-fg-2'"
        >
          {{ paused ? '已暂停' : media.seasons.length > 1 ? `共 ${media.seasons.length} 季` : '第 1 季' }}
        </span>
        <Badge :tone="media.missing.length ? 'warn' : 'good'">
          {{ media.missing.length ? `缺 ${media.missing.length} 集` : '已齐' }}
        </Badge>
      </div>

      <!-- 调用方操作入口（绝对定位右上角） -->
      <div class="absolute right-2.5 top-2.5 z-20">
        <slot name="actions" />
      </div>

      <!-- 底部暗影自然过渡蒙版与标题 -->
      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-bg via-bg/80 to-transparent p-3 pt-12">
        <h3 class="truncate text-sm font-semibold text-fg tracking-tight drop-shadow-md" :title="media.title">
          {{ media.title }}
        </h3>
      </div>
    </div>

    <!-- 底部极简进度排版 -->
    <div class="p-3 pt-2.5 space-y-2 bg-surface-solid/40">
      <div class="flex items-center justify-between text-[11px] text-muted">
        <span>追更进度</span>
        <span class="tabular-num font-medium text-fg-2">
          {{ media.owned_count }} <span class="text-faint">/</span> {{ media.aired_count }} 集
        </span>
      </div>

      <!-- 进度条 -->
      <div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-2/80">
        <div
          class="h-full rounded-full transition-all duration-500 ease-out"
          :class="media.missing.length ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.3)]' : 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.3)]'"
          :style="{ width: `${percent}%` }"
        />
      </div>

      <div class="flex items-center justify-between text-[11px] text-subtle pt-0.5">
        <span>{{ percent === 100 ? '全集已入库' : `待补 ${media.missing.length} 集` }}</span>
        <span class="text-muted group-hover:text-fg transition-colors">查看季集 →</span>
      </div>
    </div>
  </article>
</template>
