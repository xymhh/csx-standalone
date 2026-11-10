<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  Eye,
  Film,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Tabs from '@/components/ui/Tabs.vue'
import MediaDrawer from '@/components/domain/MediaDrawer.vue'
import MediaPosterCard from '@/components/domain/MediaPosterCard.vue'
import { useToast } from '@/composables/useToast'
import { progressApi, subscriptionsApi, type ProgressItem } from '@/api/subscriptions'
import { tasksApi } from '@/api/transfer'

// 追剧墙 widget：顶栏统计 + 海报墙 + 抽屉/菜单/删除/添加弹窗，状态自包含
const { toast } = useToast()
const queryClient = useQueryClient()

// 追剧清单是主查询（决定 loading 与失败提示）；转存任务仅供顶栏统计（失败仅告警）
const progressQuery = useQuery({
  queryKey: ['progress', 'overview'],
  queryFn: () => progressApi.overview(),
})
const items = computed(() => progressQuery.data.value ?? [])
const loading = computed(() => progressQuery.isLoading.value)
watch(
  () => progressQuery.error.value,
  (cause) => {
    if (cause) toast(cause instanceof Error ? cause.message : '追剧清单加载失败', 'error')
  },
)

const tasksQuery = useQuery({
  queryKey: ['tasks'],
  queryFn: () => tasksApi.list(),
})
const tasks = computed(() => tasksQuery.data.value ?? [])
watch(
  () => tasksQuery.error.value,
  (cause) => {
    if (cause) console.warn('转存任务加载失败', cause)
  },
)

const selectedMediaId = ref<number | null>(null)
const drawerOpen = ref(false)

const statusFilter = ref('all')
const statusTabs = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '追更中' },
  { value: 'paused', label: '已暂停' },
]
const filteredItems = computed(() =>
  statusFilter.value === 'all'
    ? items.value
    : items.value.filter((item) => item.subscription_state === statusFilter.value),
)

const menuOpen = ref(false)
const menuItem = ref<ProgressItem | null>(null)
const menuPos = ref({ top: 0, left: 0 })
const deleteOpen = ref(false)
const deleteTarget = ref<ProgressItem | null>(null)
const acting = ref(false)

// 添加追剧弹窗状态
const addOpen = ref(false)
const title = ref('')
const mediaType = ref('tv')
const year = ref<number | undefined>(new Date().getFullYear())
const seasonNumber = ref(1)
const episodeCount = ref(12)
const tmdbId = ref<number | undefined>(undefined)
const showAdvanced = ref(false)
const adding = ref(false)

async function load() {
  // 追剧清单先行，其余查询经缓存失效在后台补齐（与拆分前的并发方式等价）
  const progressPromise = progressQuery.refetch()
  void queryClient.invalidateQueries({ queryKey: ['doctor'] })
  void queryClient.invalidateQueries({ queryKey: ['tasks'] })
  await progressPromise
}

function openMedia(id: number) {
  selectedMediaId.value = id
  drawerOpen.value = true
}

function openMenu(media: ProgressItem, event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const width = 192
  menuPos.value = {
    top: Math.min(rect.bottom + 8, window.innerHeight - 220),
    left: Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)),
  }
  menuItem.value = media
  menuOpen.value = true
}

async function toggleSubscription() {
  const item = menuItem.value
  if (!item?.subscription_id) return
  const nextState = item.subscription_state === 'active' ? 'paused' : 'active'
  acting.value = true
  try {
    await subscriptionsApi.update(item.subscription_id, { state: nextState })
    menuOpen.value = false
    toast(
      nextState === 'active' ? `已恢复《${item.title}》追更` : `已暂停《${item.title}》追更`,
      'success',
    )
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '操作失败', 'error')
  } finally {
    acting.value = false
  }
}

function viewFromMenu() {
  const item = menuItem.value
  menuOpen.value = false
  if (item) openMedia(item.media_id)
}

function askDelete() {
  deleteTarget.value = menuItem.value
  menuOpen.value = false
  deleteOpen.value = true
}

async function confirmDelete() {
  const item = deleteTarget.value
  if (!item?.subscription_id) return
  acting.value = true
  try {
    await subscriptionsApi.delete(item.subscription_id)
    deleteOpen.value = false
    deleteTarget.value = null
    toast(`已删除《${item.title}》追剧`, 'success')
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '删除失败', 'error')
  } finally {
    acting.value = false
  }
}

async function createSubscription() {
  if (!title.value.trim()) {
    toast('请输入影视片名', 'error')
    return
  }
  adding.value = true
  try {
    await subscriptionsApi.create({
      title: title.value.trim(),
      media_type: mediaType.value,
      year: year.value || undefined,
      season_number: mediaType.value === 'tv' ? seasonNumber.value : 1,
      episode_count: mediaType.value === 'tv' ? episodeCount.value : 1,
      tmdb_id: tmdbId.value || undefined,
    })
    addOpen.value = false
    title.value = ''
    tmdbId.value = undefined
    toast('追更添加成功！系统已开始全网找源转存', 'success')
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '添加失败', 'error')
  } finally {
    adding.value = false
  }
}

const totalMissing = () => items.value.reduce((total, item) => total + item.missing.length, 0)
const runningTasks = () => tasks.value.filter((t) => t.state === 'running')
</script>

<template>
  <div>
    <!-- 顶栏精美控制区域：大字排版 + 呼吸感微数据 + 醒目操作按钮 -->
    <div class="flex flex-wrap items-end justify-between gap-4 border-b border-primary/[0.06] pb-6">
      <div>
        <div class="flex items-center gap-3">
          <h2 class="text-2xl font-bold tracking-tight text-fg">我的追剧</h2>
          <Badge tone="good" pulse>自动监控中</Badge>
        </div>
        <p class="mt-1.5 text-xs text-muted">
          已关注 <span class="font-mono font-semibold text-fg-2">{{ items.length }}</span> 部影视 ·
          待补集数 <span class="font-mono font-semibold text-amber-400">{{ totalMissing() }}</span> 集 ·
          正在转存 <span class="font-mono font-semibold text-sky-400">{{ runningTasks().length }}</span> 个文件
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <RouterLink to="/discover">
          <Button variant="outline" size="sm" class="flex items-center gap-1.5 border-surface-2 text-fg-2 hover:text-fg">
            <Search class="h-3.5 w-3.5" />
            <span>全网搜源</span>
          </Button>
        </RouterLink>
        <Button size="sm" class="flex items-center gap-1.5 shadow-md shadow-white/5" @click="addOpen = true">
          <Plus class="h-4 w-4" />
          <span>添加追剧</span>
        </Button>
      </div>
    </div>
    <!-- 核心视觉重心：2:3 电影海报墙（Poster Grid） -->
    <section class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h3 class="text-sm font-semibold tracking-tight text-fg flex items-center gap-2">
          <span>追剧清单</span>
          <span class="rounded-full bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-muted">{{ items.length }}</span>
        </h3>
        <div class="flex items-center gap-3">
          <Tabs v-model="statusFilter" :items="statusTabs" />
          <span class="whitespace-nowrap text-xs text-subtle">共 {{ filteredItems.length }} 部</span>
        </div>
      </div>

      <!-- 加载骨架：海报墙位置先占位，避免清单到达前页面跳动 -->
      <div v-if="loading && !items.length" class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
        <Skeleton v-for="n in 5" :key="n" class="aspect-[2/3] w-full" />
      </div>

      <!-- 空白占位引导 -->
      <div
        v-if="!items.length && !loading"
        class="rounded-3xl border border-dashed border-surface-2 bg-surface-solid/30 p-16 text-center"
      >
        <Film class="mx-auto mb-3 h-10 w-10 text-faint" />
        <h4 class="text-base font-semibold text-fg">追剧清单还是空的</h4>
        <p class="mt-1 text-xs text-muted max-w-sm mx-auto">
          点击右上角「+ 添加追剧」，直接输入片名即可全自动搜源转存。
        </p>
        <Button size="sm" class="mt-5" @click="addOpen = true">立即添加一部剧</Button>
      </div>

      <!-- 筛选后为空 -->
      <div
        v-else-if="!filteredItems.length"
        class="rounded-3xl border border-dashed border-surface-2 bg-surface-solid/30 p-12 text-center"
      >
        <h4 class="text-sm font-semibold text-fg">当前筛选下没有追剧</h4>
        <p class="mt-1 text-xs text-muted">切换上方状态筛选，或添加新的追剧。</p>
      </div>

      <!-- 海报卡片墙 -->
      <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
        <MediaPosterCard
          v-for="media in filteredItems"
          :key="media.media_id"
          :media="media"
          @select="openMedia"
        >
          <template #actions>
            <button
              type="button"
              class="grid h-7 w-7 place-items-center rounded-full border border-primary/15 bg-canvas text-fg-2 shadow-md transition-colors hover:bg-surface-2 hover:text-fg"
              aria-label="更多操作"
              @click.stop="openMenu(media, $event)"
            >
              <MoreHorizontal class="h-4 w-4" />
            </button>
          </template>
        </MediaPosterCard>
      </div>
    </section>    <!-- 侧滑大抽屉 -->
    <MediaDrawer
      :open="drawerOpen"
      :media-id="selectedMediaId"
      @close="drawerOpen = false"
    />

    <!-- 追剧操作菜单（不透明浮层） -->
    <Teleport to="body">
      <div v-if="menuOpen" class="fixed inset-0 z-50" @click="menuOpen = false">
        <div
          class="absolute w-48 rounded-xl border border-primary/10 bg-canvas p-1.5 shadow-2xl shadow-black/70"
          :style="{ top: `${menuPos.top}px`, left: `${menuPos.left}px` }"
          @click.stop
        >
          <p v-if="menuItem?.subscription_state" class="px-3 pb-1.5 pt-1 text-[11px] text-subtle">
            {{ menuItem.subscription_state === 'active' ? '当前追更中' : '当前已暂停' }}
          </p>
          <Button
            v-if="menuItem?.subscription_id && (menuItem.subscription_state === 'active' || menuItem.subscription_state === 'paused')"
            variant="ghost"
            class="w-full justify-start gap-2"
            :disabled="acting"
            @click="toggleSubscription"
          >
            <Pause v-if="menuItem.subscription_state === 'active'" class="h-4 w-4" />
            <Play v-else class="h-4 w-4" />
            <span>{{ menuItem.subscription_state === 'active' ? '暂停追更' : '恢复追更' }}</span>
          </Button>
          <Button variant="ghost" class="w-full justify-start gap-2" @click="viewFromMenu">
            <Eye class="h-4 w-4" />
            <span>查看详情</span>
          </Button>
          <Button
            v-if="menuItem?.subscription_id"
            variant="ghost"
            class="w-full justify-start gap-2 text-rose-400 hover:text-rose-300"
            :disabled="acting"
            @click="askDelete"
          >
            <Trash2 class="h-4 w-4" />
            <span>删除追剧</span>
          </Button>
        </div>
      </div>
    </Teleport>

    <!-- 删除追剧二次确认 -->
    <Dialog :open="deleteOpen" title="删除追剧" @close="deleteOpen = false">
      <div class="space-y-4">
        <p class="text-sm leading-relaxed text-fg-2">
          删除《{{ deleteTarget?.title }}》后将不再自动追更，已入库文件不受影响。
        </p>
        <div class="flex justify-end gap-2">
          <Button variant="ghost" @click="deleteOpen = false">取消</Button>
          <Button variant="danger" :disabled="acting" @click="confirmDelete">
            {{ acting ? '删除中…' : '确认删除' }}
          </Button>
        </div>
      </div>
    </Dialog>

    <!-- 添加追剧弹窗 -->
    <Dialog :open="addOpen" title="添加追更订阅" @close="addOpen = false">
      <form class="space-y-4" @submit.prevent="createSubscription">
        <label class="block space-y-1.5 text-sm">
          <span class="font-medium text-fg">影视名称</span>
          <Input v-model="title" required placeholder="例如：庆余年、死侍、边水往事" />
          <span class="text-xs text-subtle">直接输入中文或英文片名即可，系统自动匹配</span>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-fg">类型</span>
            <Select
              v-model="mediaType"
              :options="[
                { value: 'tv', label: '电视剧 / 动漫' },
                { value: 'movie', label: '电影' },
              ]"
            />
          </label>
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-fg">上映年份 (可选)</span>
            <Input v-model.number="year" type="number" min="1900" max="2100" placeholder="例如 2024" />
          </label>
        </div>

        <div v-if="mediaType === 'tv'" class="grid grid-cols-2 gap-3 p-3 rounded-xl border border-primary/[0.06] bg-surface-solid/40">
          <label class="block space-y-1 text-xs">
            <span class="text-muted">追更季数</span>
            <Input v-model.number="seasonNumber" type="number" min="1" max="100" />
          </label>
          <label class="block space-y-1 text-xs">
            <span class="text-muted">预计总集数</span>
            <Input v-model.number="episodeCount" type="number" min="1" max="1000" />
          </label>
        </div>

        <div>
          <button
            type="button"
            class="flex items-center gap-1.5 text-xs text-subtle hover:text-fg-2 transition-colors"
            @click="showAdvanced = !showAdvanced"
          >
            <SlidersHorizontal class="h-3 w-3" />
            <span>{{ showAdvanced ? '收起高级选项' : '高级选项 (可选填 TMDB ID)' }}</span>
          </button>
          <div v-if="showAdvanced" class="mt-2 pt-2 border-t border-primary/[0.04]">
            <label class="block space-y-1 text-xs">
              <span class="text-muted">TMDB ID</span>
              <Input v-model.number="tmdbId" type="number" placeholder="例如 94954" />
            </label>
          </div>
        </div>

        <Button type="submit" class="w-full" :disabled="adding">
          {{ adding ? '添加中…' : '立即添加并开始全网找源' }}
        </Button>
      </form>
    </Dialog>  </div>
</template>
