<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  X,
  RefreshCw,
  Search,
  ExternalLink,
  Film,
  FolderOpen,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import { posterSrc } from '@/lib/poster'
import Button from '@/components/ui/Button.vue'
import EpisodeMatrix from '@/components/domain/EpisodeMatrix.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { progressApi, type ProgressItem, type ProgressSeason } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ open: boolean; mediaId: number | null }>()
const emit = defineEmits<{ close: [] }>()

const media = ref<ProgressItem | null>(null)
const loading = ref(false)
const error = ref('')
const activeSeasonTab = ref('1')
const viewMode = ref<'matrix' | 'files'>('matrix')
const copiedPath = ref<string | null>(null)
const { toast } = useToast()

watch(
  () => [props.open, props.mediaId] as const,
  async ([open, id]) => {
    if (!open || !id) return
    loading.value = true
    error.value = ''
    try {
      media.value = await progressApi.getDetail(id)
      if (media.value?.seasons?.length) {
        activeSeasonTab.value = String(media.value.seasons[0].season)
      }
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '剧集详情加载失败'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

const currentSeason = () =>
  media.value?.seasons?.find((s) => String(s.season) === activeSeasonTab.value)

function copyFilePath(path: string) {
  navigator.clipboard.writeText(path)
  copiedPath.value = path
  toast('已复制网盘文件路径', 'success')
  setTimeout(() => {
    if (copiedPath.value === path) copiedPath.value = null
  }, 2000)
}
</script>

<template>
  <Teleport to="body">
    <!-- 苹果风格全屏暗色毛玻璃遮罩 -->
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xl transition-opacity duration-300"
      @click.self="emit('close')"
    >
      <!-- macOS Sequoia 风格侧滑大抽屉 (Sheet) -->
      <section
        role="dialog"
        aria-modal="true"
        class="relative flex h-full w-full max-w-2xl flex-col border-l border-white/[0.08] bg-zinc-950/95 shadow-2xl backdrop-blur-2xl transition-transform duration-300 ease-out"
      >
        <!-- 头部导航与关闭按钮 -->
        <header class="flex h-14 items-center justify-between border-b border-white/[0.08] px-6">
          <div class="flex items-center gap-2 text-xs text-zinc-400">
            <Film class="h-4 w-4 text-zinc-300" />
            <span class="font-medium text-white">{{ media?.title || '剧集详情' }}</span>
          </div>
          <button
            class="grid h-8 w-8 place-items-center rounded-full text-zinc-400 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="关闭"
            @click="emit('close')"
          >
            <X class="h-4 w-4" />
          </button>
        </header>

        <div v-if="loading" class="flex flex-1 items-center justify-center p-12 text-xs text-zinc-400">
          <RefreshCw class="mr-2 h-4 w-4 animate-spin text-white" />
          <span>正在读取剧集与网盘文件详情…</span>
        </div>

        <div v-else-if="error" class="p-6 text-sm text-rose-400">{{ error }}</div>

        <div v-else-if="media" class="flex-1 space-y-6 overflow-y-auto p-6 scrollbar-thin">
          <!-- 头部海报与元数据区 -->
          <div class="flex gap-5 items-start">
            <div class="h-40 w-28 shrink-0 overflow-hidden rounded-xl border border-white/10 bg-zinc-900 shadow-md">
              <img
                v-if="media.poster_url"
                :src="posterSrc(media.poster_url)"
                class="h-full w-full object-cover"
              />
              <div v-else class="grid h-full w-full place-items-center text-zinc-600">
                <Film class="h-8 w-8 opacity-40" />
              </div>
            </div>

            <div class="space-y-2 min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-xl font-bold tracking-tight text-white">{{ media.title }}</h3>
                <Badge :tone="media.missing.length ? 'warn' : 'good'">
                  {{ media.missing.length ? `缺 ${media.missing.length} 集` : '全集已入库' }}
                </Badge>
              </div>

              <p class="text-xs text-zinc-400">
                上映：{{ media.year || '未知' }} · 类型：{{ media.type === 'movie' ? '电影' : '电视剧' }} ·
                入库进度：{{ media.owned_count }} / {{ media.aired_count }} 集
              </p>

              <p v-if="media.overview" class="text-xs text-zinc-300 leading-relaxed line-clamp-3">
                {{ media.overview }}
              </p>

              <!-- 快捷操作栏 -->
              <div class="flex flex-wrap gap-2 pt-1">
                <RouterLink :to="`/search?q=${encodeURIComponent(media.title)}`">
                  <Button variant="outline" size="sm" class="h-7 text-xs">
                    <Search class="mr-1 h-3 w-3" />
                    全网重新找源
                  </Button>
                </RouterLink>
              </div>
            </div>
          </div>

          <!-- 季选项卡 (Segmented Control) -->
          <div v-if="media.seasons.length > 1" class="border-t border-white/[0.06] pt-4">
            <Tabs
              v-model="activeSeasonTab"
              :items="media.seasons.map((s) => ({ value: String(s.season), label: `第 ${s.season} 季` }))"
            />
          </div>

          <!-- 选集状态与展示视图切换 -->
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                选集与真实网盘文件
              </span>
              <div class="inline-flex rounded-lg border border-white/10 bg-zinc-900/60 p-0.5 text-xs">
                <button
                  type="button"
                  class="rounded-md px-2.5 py-1 font-medium transition-colors"
                  :class="viewMode === 'matrix' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400'"
                  @click="viewMode = 'matrix'"
                >
                  方格矩阵
                </button>
                <button
                  type="button"
                  class="rounded-md px-2.5 py-1 font-medium transition-colors"
                  :class="viewMode === 'files' ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400'"
                  @click="viewMode = 'files'"
                >
                  文件清单
                </button>
              </div>
            </div>

            <!-- 1. 选集方格矩阵视图 -->
            <div v-if="viewMode === 'matrix'" class="space-y-4">
              <div v-if="currentSeason()" class="space-y-2">
                <div class="grid grid-cols-[repeat(auto-fill,minmax(48px,1fr))] gap-2">
                  <div
                    v-for="ep in currentSeason()!.episodes"
                    :key="ep.episode"
                    class="group relative flex aspect-square flex-col items-center justify-center rounded-xl border text-xs font-mono font-medium transition-all"
                    :class="
                      ep.owned
                        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                        : ep.aired
                          ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                          : 'border-white/[0.06] bg-zinc-900/40 text-zinc-600'
                    "
                    :title="ep.file?.path ? `已入库文件: ${ep.file.path}` : `第 ${ep.episode} 集 (待转存)`"
                  >
                    <span>{{ String(ep.episode).padStart(2, '0') }}</span>
                    <span v-if="ep.file?.quality_bucket" class="text-[9px] uppercase font-sans text-emerald-500/80">
                      {{ ep.file.quality_bucket }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 2. 文件详细清单视图（逐集网盘文件与大小） -->
            <div v-else class="space-y-2.5">
              <div v-if="currentSeason()" class="divide-y divide-white/[0.06] rounded-xl border border-white/[0.08] bg-zinc-900/40 overflow-hidden">
                <div
                  v-for="ep in currentSeason()!.episodes"
                  :key="ep.episode"
                  class="p-3 text-xs flex items-center justify-between gap-3 hover:bg-white/[0.02] transition-colors"
                >
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <span class="font-mono font-semibold text-white">E{{ String(ep.episode).padStart(2, '0') }}</span>
                      <span class="truncate text-zinc-300 font-medium">{{ ep.title || `第 ${ep.episode} 集` }}</span>
                      <Badge :tone="ep.owned ? 'good' : 'warn'">
                        {{ ep.owned ? '已在网盘' : '待补缺集' }}
                      </Badge>
                    </div>

                    <p v-if="ep.file" class="mt-1 font-mono text-[11px] text-zinc-400 truncate" :title="ep.file.path">
                      {{ ep.file.path }}
                    </p>
                  </div>

                  <div v-if="ep.file" class="flex items-center gap-2 shrink-0">
                    <Badge tone="info" class="uppercase font-mono">{{ ep.file.quality_bucket }}</Badge>
                    <span class="font-mono text-zinc-500 tabular-num text-[11px]">
                      {{ (ep.file.size / 1024 ** 3).toFixed(2) }} GB
                    </span>
                    <Button variant="ghost" size="sm" class="h-7 w-7 p-0" title="复制路径" @click="copyFilePath(ep.file.path)">
                      <component :is="copiedPath === ep.file.path ? Check : Copy" class="h-3 w-3" />
                    </Button>
                  </div>

                  <div v-else class="shrink-0">
                    <RouterLink :to="`/search?q=${encodeURIComponent(`${media.title} S${String(currentSeason()!.season).padStart(2, '0')}E${String(ep.episode).padStart(2, '0')}`)}`">
                      <Button variant="outline" size="sm" class="h-7 text-[11px]">搜这集</Button>
                    </RouterLink>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </Teleport>
</template>
