<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import EpisodeMatrix from '@/components/domain/EpisodeMatrix.vue'
import { progressApi, type ProgressItem } from '@/lib/api'

const props = defineProps<{ open: boolean; mediaId: number | null }>()
const emit = defineEmits<{ close: [] }>()
const media = ref<ProgressItem | null>(null)
const loading = ref(false)
const error = ref('')

watch(() => [props.open, props.mediaId] as const, async ([open, id]) => {
  if (!open || !id) return
  loading.value = true
  error.value = ''
  try {
    media.value = await progressApi.getDetail(id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '剧集详情加载失败'
  } finally {
    loading.value = false
  }
}, { immediate: true })
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-md" @click.self="emit('close')">
      <aside class="absolute inset-y-0 right-0 flex w-full max-w-2xl flex-col border-l border-border bg-surface shadow-2xl shadow-black/50">
        <header class="flex items-start justify-between gap-4 border-b border-border/70 p-5 sm:p-7">
          <div>
            <p class="text-xs font-medium uppercase tracking-[0.18em] text-muted">媒体详情</p>
            <h2 class="mt-1 text-xl font-semibold tracking-tight text-fg">{{ media?.title ?? '正在加载…' }}</h2>
            <p v-if="media" class="mt-1 text-sm text-muted">{{ media.year || '年份未知' }} · {{ media.type === 'movie' ? '电影' : '剧集' }}</p>
          </div>
          <button class="grid min-h-11 min-w-11 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg" aria-label="关闭媒体详情" @click="emit('close')"><X class="h-5 w-5" /></button>
        </header>
        <div class="flex-1 space-y-6 overflow-y-auto p-5 sm:p-7">
          <p v-if="error" class="rounded-lg border border-status-missing/30 bg-status-missing/10 p-3 text-sm text-status-missing">{{ error }}</p>
          <div v-else-if="loading && !media" class="py-16 text-center text-sm text-muted">正在读取详情…</div>
          <template v-else-if="media">
            <section class="flex gap-5">
              <img v-if="media.poster_url" :src="media.poster_url" :alt="`${media.title} 海报`" class="w-28 shrink-0 self-start rounded-xl object-cover shadow-lg sm:w-36" />
              <div class="min-w-0 space-y-3">
                <div class="flex flex-wrap gap-2"><Badge tone="muted">{{ media.owned_count }} / {{ media.aired_count }} 集入库</Badge><Badge :tone="media.missing.length ? 'warn' : 'good'">{{ media.missing.length ? `缺 ${media.missing.length} 集` : '全集已齐' }}</Badge></div>
                <p class="text-sm leading-6 text-muted">{{ media.overview || '暂无简介。' }}</p>
              </div>
            </section>
            <section class="space-y-3">
              <h3 class="text-sm font-semibold text-fg">季集与网盘文件</h3>
              <div v-for="season in media.seasons" :key="season.season" class="rounded-xl border border-border/70 bg-bg/30 p-4">
                <h4 class="mb-3 text-sm font-medium text-fg">第 {{ season.season }} 季</h4>
                <div class="space-y-2">
                  <div v-for="episode in season.episodes" :key="episode.episode" class="rounded-lg border border-border/50 bg-surface/60 p-3">
                    <div class="flex items-center justify-between gap-3"><span class="text-sm font-medium text-fg">E{{ String(episode.episode).padStart(2, '0') }} {{ episode.title || '' }}</span><Badge :tone="episode.owned ? 'good' : 'muted'">{{ episode.owned ? episode.file?.quality_bucket?.toUpperCase() || '已入库' : '缺失' }}</Badge></div>
                    <div v-if="episode.file" class="mt-2 space-y-1 text-xs text-muted"><p class="break-all font-mono">{{ episode.file.path }}</p><p class="tabular-nums">{{ (episode.file.size / 1024 / 1024 / 1024).toFixed(2) }} GB · {{ new Date(episode.file.created_at).toLocaleDateString() }}</p></div>
                  </div>
                </div>
              </div>
            </section>
          </template>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
