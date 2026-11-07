<script setup lang="ts">
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import type { Candidate } from '@/lib/api'

defineProps<{ candidate: Candidate }>()
defineEmits<{ accept: [id: number]; ignore: [id: number] }>()
</script>

<template>
  <article class="surface-card group relative overflow-hidden p-5 transition-colors hover:border-zinc-700">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="mb-1.5 font-mono text-[11px] uppercase tracking-wider text-muted">
          网盘：{{ candidate.provider }}
        </p>
        <h3 class="break-all font-semibold tracking-tight text-fg text-base">
          {{ candidate.payload.title ?? (candidate.share_url || `分享链接 #${candidate.id}`) }}
        </h3>
        <p class="mt-1 text-xs text-muted">关联追剧 #{{ candidate.subscription_id }}</p>
      </div>
      <Badge tone="info">推荐度 {{ candidate.score }}</Badge>
    </div>
    <p v-if="candidate.payload.quality_bucket" class="mt-3.5 rounded-lg bg-surface-2/60 px-3 py-2 text-xs text-muted flex items-center justify-between">
      <span>识别画质版本</span>
      <span class="font-mono font-medium text-fg uppercase">{{ candidate.payload.quality_bucket }}</span>
    </p>
    <div class="mt-4 flex flex-wrap gap-2 pt-2 border-t border-border/50">
      <Button @click="$emit('accept', candidate.id)">转存到我的网盘</Button>
      <Button variant="outline" @click="$emit('ignore', candidate.id)">忽略该资源</Button>
    </div>
  </article>
</template>
