<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Compass, Film, Star, Plus, Check } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useToast } from '@/composables/useToast'
import { subscriptionsApi, tmdbApi, type TmdbItem } from '@/lib/api'

const tabs = [
  { value: 'trending', label: '流行趋势' },
  { value: 'showing', label: '正在热映' },
  { value: 'movie_hot', label: '热门电影' },
  { value: 'tv_hot', label: '热门剧集' },
  { value: 'calendar', label: '每日放送' },
  { value: 'season', label: '本季新番' },
]
const activeTab = ref('trending')
const items = ref<TmdbItem[]>([])
const loading = ref(false)
const { toast } = useToast()

const typeFilter = ref<'all' | 'movie' | 'tv'>('all')
const yearFilter = ref<'all' | 'this' | 'recent'>('all')
const ratingFilter = ref<'all' | '7' | '8' | '9'>('all')
const currentYear = new Date().getFullYear()

const filteredItems = computed(() => {
  return items.value.filter((item) => {
    if (typeFilter.value !== 'all' && item.type !== typeFilter.value) return false
    if (yearFilter.value === 'this' && item.year !== currentYear) return false
    if (yearFilter.value === 'recent' && (item.year === null || item.year < currentYear - 2)) {
      return false
    }
    if (ratingFilter.value !== 'all' && item.vote_average < Number(ratingFilter.value)) {
      return false
    }
    return true
  })
})

// 详情弹窗
const selected = ref<TmdbItem | null>(null)
const detailOpen = ref(false)
const subscribing = ref(false)
const subscribedIds = ref<Set<number>>(new Set())

async function loadSubscribed() {
  try {
    const subs = await subscriptionsApi.list()
    const set = new Set<number>()
    for (const s of subs) {
      if (s.media?.tmdb_id) set.add(s.media.tmdb_id)
    }
    subscribedIds.value = set
  } catch {}
}

async function fetchItems() {
  loading.value = true
  items.value = []
  try {
    if (activeTab.value === 'trending') {
      items.value = await tmdbApi.trending()
    } else if (activeTab.value === 'showing') {
      items.value = await tmdbApi.douban('showing')
    } else if (activeTab.value === 'movie_hot') {
      items.value = await tmdbApi.douban('movie_hot')
    } else if (activeTab.value === 'tv_hot') {
      items.value = await tmdbApi.douban('tv_hot')
    } else if (activeTab.value === 'calendar') {
      items.value = await tmdbApi.bangumiCalendar()
    } else if (activeTab.value === 'season') {
      items.value = await tmdbApi.anilistSeason()
    }
  } catch (cause) {
    toast('获取推荐榜单失败，请稍后重试', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void fetchItems()
  void loadSubscribed()
})

watch(activeTab, () => {
  void fetchItems()
})

function openDetail(item: TmdbItem) {
  selected.value = item
  detailOpen.value = true
}

async function subscribeItem() {
  if (!selected.value) return
  subscribing.value = true
  try {
    let target = selected.value
    let tmdbId = selected.value.id

    if (tmdbId < 0) {
      const matches = await tmdbApi.search(selected.value.title)
      const first = matches.find((item) => item.id > 0)
      if (!first) {
        toast(`TMDB 未收录《${selected.value.title}》，无法加入追剧`, 'error')
        return
      }
      target = first
      tmdbId = first.id
    }

    await subscriptionsApi.create({
      title: target.title,
      media_type: target.type,
      year: target.year || undefined,
      tmdb_id: tmdbId,
      season_number: 1,
      episode_count: 24,
    })
    subscribedIds.value.add(tmdbId)
    toast(`已添加《${target.title}》！系统已开始全网找源转存`, 'success')
    detailOpen.value = false
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '添加追剧失败', 'error')
  } finally {
    subscribing.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold tracking-tight text-fg flex items-center gap-2">
          <span>探索发现</span>
          <Badge tone="good">多源热播榜</Badge>
        </h2>
        <p class="mt-1 text-xs text-muted">全网热播影视风向标，点击任意海报即可一键加入追更</p>
      </div>
    </div>

    <!-- 顶部清晰选项卡 -->
    <Tabs v-model="activeTab" :items="tabs" />

    <!-- 筛选条 -->
    <div
      v-if="!loading && items.length"
      class="flex flex-wrap items-center gap-3 rounded-2xl border border-border/60 bg-surface/60 px-4 py-3 text-xs"
    >
      <label class="flex items-center gap-2">
        <span class="text-subtle">类型</span>
        <select
          v-model="typeFilter"
          class="rounded-lg border border-border/70 bg-surface-2/60 px-2.5 py-1.5 text-xs text-fg outline-none focus:border-zinc-500"
        >
          <option value="all">全部</option>
          <option value="movie">电影</option>
          <option value="tv">剧集</option>
        </select>
      </label>
      <label class="flex items-center gap-2">
        <span class="text-subtle">年份</span>
        <select
          v-model="yearFilter"
          class="rounded-lg border border-border/70 bg-surface-2/60 px-2.5 py-1.5 text-xs text-fg outline-none focus:border-zinc-500"
        >
          <option value="all">全部</option>
          <option value="this">今年</option>
          <option value="recent">近三年</option>
        </select>
      </label>
      <label class="flex items-center gap-2">
        <span class="text-subtle">评分</span>
        <select
          v-model="ratingFilter"
          class="rounded-lg border border-border/70 bg-surface-2/60 px-2.5 py-1.5 text-xs text-fg outline-none focus:border-zinc-500"
        >
          <option value="all">全部</option>
          <option value="7">7+</option>
          <option value="8">8+</option>
          <option value="9">9+</option>
        </select>
      </label>
      <span class="ml-auto text-subtle">共 {{ filteredItems.length }} 条</span>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loading" class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
      <div
        v-for="i in 10"
        :key="i"
        class="aspect-[2/3] rounded-2xl border border-border/40 bg-surface-2/30 animate-pulse"
      />
    </div>

    <!-- 空状态优雅提示 -->
    <div
      v-else-if="!items.length"
      class="rounded-2xl border border-dashed border-border/80 bg-surface/30 p-16 text-center space-y-3"
    >
      <Compass class="mx-auto h-10 w-10 text-subtle/50" />
      <h3 class="text-base font-semibold text-fg">该榜单暂时没有数据，稍后再试</h3>
      <p class="text-xs text-muted max-w-sm mx-auto">数据源可能暂时不可用，你可以稍后重试或切换其他榜单。</p>
      <div class="flex items-center justify-center gap-3 pt-2">
        <Button variant="outline" size="sm" @click="fetchItems">重试拉取</Button>
      </div>
    </div>

    <!-- 筛选后为空 -->
    <div
      v-else-if="!filteredItems.length"
      class="rounded-2xl border border-dashed border-border/80 bg-surface/30 p-16 text-center space-y-3"
    >
      <Compass class="mx-auto h-10 w-10 text-subtle/50" />
      <h3 class="text-base font-semibold text-fg">没有符合筛选条件的条目</h3>
      <p class="text-xs text-muted max-w-sm mx-auto">试试调整类型、年份或评分筛选。</p>
    </div>

    <!-- 2:3 电影海报流 -->
    <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
      <article
        v-for="item in filteredItems"
        :key="item.id"
        class="group relative flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-surface/80 shadow-sm transition-all duration-200 hover:-translate-y-1.5 hover:border-zinc-700 hover:shadow-xl hover:shadow-black/60 cursor-pointer"
        @click="openDetail(item)"
      >
        <!-- 海报图 (2:3 国际标准海报比例) -->
        <div class="relative aspect-[2/3] w-full overflow-hidden bg-surface-2">
          <img
            v-if="item.poster_url"
            :src="item.poster_url"
            :alt="item.title"
            loading="lazy"
            class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
          <div v-else class="grid h-full w-full place-items-center bg-zinc-900 text-subtle">
            <Film class="h-10 w-10 opacity-30" />
          </div>

          <!-- 顶部评分与类型胶囊 -->
          <div class="absolute inset-x-2.5 top-2.5 flex items-center justify-between">
            <span class="rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-zinc-300 backdrop-blur-md uppercase">
              {{ item.type === 'movie' ? '电影' : '剧集' }}
            </span>
            <span
              v-if="item.vote_average > 0"
              class="flex items-center gap-1 rounded-md bg-black/70 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-amber-400 backdrop-blur-md shadow-sm"
            >
              <Star class="h-3 w-3 fill-amber-400 text-amber-400" />
              <span>{{ item.vote_average.toFixed(1) }}</span>
            </span>
          </div>

          <!-- 已追剧状态角标 -->
          <div
            v-if="subscribedIds.has(item.id)"
            class="absolute bottom-2.5 right-2.5 rounded-md bg-emerald-500/90 px-2 py-0.5 text-[10px] font-medium text-white shadow-md backdrop-blur-md flex items-center gap-1"
          >
            <Check class="h-3 w-3" />
            <span>已在追更</span>
          </div>
        </div>

        <!-- 卡片底部标题与年份 -->
        <div class="p-3">
          <h3 class="truncate text-sm font-semibold text-fg tracking-tight" :title="item.title">
            {{ item.title }}
          </h3>
          <div class="mt-1 flex items-center justify-between text-[11px] text-subtle">
            <span>{{ item.year || '近期' }}</span>
            <span class="text-zinc-400 group-hover:text-fg transition-colors">查看详情 →</span>
          </div>
        </div>
      </article>
    </div>

    <!-- 影视详情与一键追剧弹窗 (大剧照 + 介绍) -->
    <Dialog :open="detailOpen" :title="selected?.title ?? '影视详情'" @close="detailOpen = false">
      <div v-if="selected" class="space-y-4">
        <!-- 背景大剧照 -->
        <div
          v-if="selected.backdrop_url"
          class="relative h-44 w-full overflow-hidden rounded-xl bg-surface-2 -mt-1"
        >
          <img :src="selected.backdrop_url" class="h-full w-full object-cover" />
          <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/40 to-transparent" />
          <div class="absolute bottom-3 left-4 right-4 flex items-end justify-between">
            <div>
              <h3 class="text-xl font-bold text-fg drop-shadow-md">{{ selected.title }}</h3>
              <p class="text-xs text-zinc-300 drop-shadow">{{ selected.year }} · {{ selected.type === 'movie' ? '电影' : '电视剧' }}</p>
            </div>
            <span class="flex items-center gap-1 rounded-md bg-black/70 px-2 py-1 font-mono text-sm font-bold text-amber-400 backdrop-blur-md">
              <Star class="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
              <span>{{ selected.vote_average.toFixed(1) }}</span>
            </span>
          </div>
        </div>

        <!-- 剧情简介 -->
        <div class="space-y-1.5 text-xs text-muted">
          <span class="font-medium text-fg">剧情简介</span>
          <p class="leading-relaxed line-clamp-4 text-zinc-300">
            {{ selected.overview || '暂无详细简介。' }}
          </p>
        </div>

        <!-- 底部一键操作 -->
        <div class="pt-2">
          <Button
            v-if="!subscribedIds.has(selected.id)"
            class="w-full flex items-center justify-center gap-2"
            :disabled="subscribing"
            @click="subscribeItem"
          >
            <Plus class="h-4 w-4" />
            <span>{{ subscribing ? '正在添加…' : '加入我的追剧（全网自动找源）' }}</span>
          </Button>
          <div v-else class="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-center text-xs font-medium text-emerald-400 flex items-center justify-center gap-1.5">
            <Check class="h-4 w-4" />
            <span>该影视已在你的追剧清单中，系统正在自动监控</span>
          </div>
        </div>
      </div>
    </Dialog>
  </div>
</template>
