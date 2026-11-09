<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Activity,
  AlertCircle,
  Clapperboard,
  DownloadCloud,
  Film,
  Eye,
  HardDrive,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Trash2,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Tabs from '@/components/ui/Tabs.vue'
import MediaDrawer from '@/components/domain/MediaDrawer.vue'
import MediaPosterCard from '@/components/domain/MediaPosterCard.vue'
import TaskRow from '@/components/domain/TaskRow.vue'
import { useEvents } from '@/composables/useEvents'
import { useToast } from '@/composables/useToast'
import {
  doctorApi,
  progressApi,
  subscriptionsApi,
  tasksApi,
  type DoctorReport,
  type ProgressItem,
  type Task,
} from '@/lib/api'

const { toast } = useToast()
const report = ref<DoctorReport | null>(null)
const items = ref<ProgressItem[]>([])
const tasks = ref<Task[]>([])
const loading = ref(true)
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
  // 三项互不依赖，任何一个变慢或失败都不应把追剧清单一起拖空
  const [doctorResult, progressResult, tasksResult] = await Promise.allSettled([
    doctorApi.diagnose(),
    progressApi.overview(),
    tasksApi.list(),
  ])
  if (doctorResult.status === 'fulfilled') {
    report.value = doctorResult.value
  } else {
    console.warn('系统自检失败', doctorResult.reason)
  }
  if (progressResult.status === 'fulfilled') {
    items.value = progressResult.value
  } else {
    toast(progressResult.reason instanceof Error ? progressResult.reason.message : '追剧清单加载失败', 'error')
  }
  if (tasksResult.status === 'fulfilled') {
    tasks.value = tasksResult.value
  } else {
    console.warn('转存任务加载失败', tasksResult.reason)
  }
  loading.value = false
}

onMounted(load)
useEvents((event) => {
  if (event.type === 'task_status' || event.type === 'progress_update') void load()
})

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
  <div class="space-y-8">
    <!-- 顶栏精美控制区域：大字排版 + 呼吸感微数据 + 醒目操作按钮 -->
    <div class="flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.06] pb-6">
      <div>
        <div class="flex items-center gap-3">
          <h2 class="text-2xl font-bold tracking-tight text-white">我的追剧</h2>
          <Badge tone="good" pulse>自动监控中</Badge>
        </div>
        <p class="mt-1.5 text-xs text-zinc-400">
          已关注 <span class="font-mono font-semibold text-zinc-200">{{ items.length }}</span> 部影视 ·
          待补集数 <span class="font-mono font-semibold text-amber-400">{{ totalMissing() }}</span> 集 ·
          正在转存 <span class="font-mono font-semibold text-sky-400">{{ runningTasks().length }}</span> 个文件
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <RouterLink to="/discover">
          <Button variant="outline" size="sm" class="flex items-center gap-1.5 border-zinc-800 text-zinc-300 hover:text-white">
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
        <h3 class="text-sm font-semibold tracking-tight text-white flex items-center gap-2">
          <span>追剧清单</span>
          <span class="rounded-full bg-zinc-800 px-2 py-0.5 font-mono text-[11px] text-zinc-400">{{ items.length }}</span>
        </h3>
        <div class="flex items-center gap-3">
          <Tabs v-model="statusFilter" :items="statusTabs" />
          <span class="whitespace-nowrap text-xs text-zinc-500">共 {{ filteredItems.length }} 部</span>
        </div>
      </div>

      <!-- 空白占位引导 -->
      <div
        v-if="!items.length && !loading"
        class="rounded-3xl border border-dashed border-zinc-800 bg-zinc-900/30 p-16 text-center"
      >
        <Film class="mx-auto mb-3 h-10 w-10 text-zinc-600" />
        <h4 class="text-base font-semibold text-white">追剧清单还是空的</h4>
        <p class="mt-1 text-xs text-zinc-400 max-w-sm mx-auto">
          点击右上角「+ 添加追剧」，直接输入片名即可全自动搜源转存。
        </p>
        <Button size="sm" class="mt-5" @click="addOpen = true">立即添加一部剧</Button>
      </div>

      <!-- 筛选后为空 -->
      <div
        v-else-if="!filteredItems.length"
        class="rounded-3xl border border-dashed border-zinc-800 bg-zinc-900/30 p-12 text-center"
      >
        <h4 class="text-sm font-semibold text-white">当前筛选下没有追剧</h4>
        <p class="mt-1 text-xs text-zinc-400">切换上方状态筛选，或添加新的追剧。</p>
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
              class="grid h-7 w-7 place-items-center rounded-full border border-white/15 bg-zinc-950 text-zinc-200 shadow-md transition-colors hover:bg-zinc-800 hover:text-white"
              aria-label="更多操作"
              @click.stop="openMenu(media, $event)"
            >
              <MoreHorizontal class="h-4 w-4" />
            </button>
          </template>
        </MediaPosterCard>
      </div>
    </section>

    <!-- 底部状态与转存队列横幅（无冗余套娃边框，轻盈现代） -->
    <section class="grid gap-5 lg:grid-cols-12 pt-2">
      <!-- 正在进行的转存任务 -->
      <div class="lg:col-span-8 rounded-2xl border border-white/[0.06] bg-zinc-900/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <DownloadCloud class="h-4 w-4 text-sky-400" />
            <h4 class="text-sm font-semibold text-white">转存队列</h4>
          </div>
          <RouterLink to="/tasks" class="text-xs text-zinc-400 hover:text-white transition-colors">查看全部任务 →</RouterLink>
        </div>

        <div v-if="!tasks.length" class="py-6 text-center text-xs text-zinc-500">
          暂无正在处理的任务，所有入库文件均已就绪
        </div>
        <div v-else class="space-y-2">
          <TaskRow
            v-for="task in tasks.slice(0, 3)"
            :key="task.id"
            :task="task"
            @retry="(id) => tasksApi.retry(id).then(() => toast('任务已重新排队', 'success'))"
          />
        </div>
      </div>

      <!-- 系统健康状态指标 -->
      <div class="lg:col-span-4 rounded-2xl border border-white/[0.06] bg-zinc-900/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-emerald-400" />
            <h4 class="text-sm font-semibold text-white">系统运行状态</h4>
          </div>
          <Badge tone="good">正常</Badge>
        </div>

        <div class="space-y-2.5 pt-1 text-xs">
          <div class="flex items-center justify-between text-zinc-400">
            <span class="flex items-center gap-2">
              <HardDrive class="h-3.5 w-3.5 text-zinc-500" />
              <span>本地 SQLite 存储</span>
            </span>
            <span class="font-mono text-zinc-300">正常</span>
          </div>
          <div class="flex items-center justify-between text-zinc-400 border-t border-white/[0.04] pt-2.5">
            <span class="flex items-center gap-2">
              <RefreshCw class="h-3.5 w-3.5 text-zinc-500" />
              <span>全天候自动轮询</span>
            </span>
            <span class="text-emerald-400 font-medium">30s 巡检</span>
          </div>
          <div class="flex items-center justify-between text-zinc-400 border-t border-white/[0.04] pt-2.5">
            <span class="flex items-center gap-2">
              <Sparkles class="h-3.5 w-3.5 text-zinc-500" />
              <span>网盘账号安全保护</span>
            </span>
            <span class="text-emerald-400 font-medium">Fernet 密保</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 侧滑大抽屉 -->
    <MediaDrawer
      :open="drawerOpen"
      :media-id="selectedMediaId"
      @close="drawerOpen = false"
    />

    <!-- 追剧操作菜单（不透明浮层） -->
    <Teleport to="body">
      <div v-if="menuOpen" class="fixed inset-0 z-50" @click="menuOpen = false">
        <div
          class="absolute w-48 rounded-xl border border-white/10 bg-zinc-950 p-1.5 shadow-2xl shadow-black/70"
          :style="{ top: `${menuPos.top}px`, left: `${menuPos.left}px` }"
          @click.stop
        >
          <p v-if="menuItem?.subscription_state" class="px-3 pb-1.5 pt-1 text-[11px] text-zinc-500">
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
        <p class="text-sm leading-relaxed text-zinc-300">
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
          <span class="font-medium text-white">影视名称</span>
          <Input v-model="title" required placeholder="例如：庆余年、死侍、边水往事" />
          <span class="text-xs text-zinc-500">直接输入中文或英文片名即可，系统自动匹配</span>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-white">类型</span>
            <Select
              v-model="mediaType"
              :options="[
                { value: 'tv', label: '电视剧 / 动漫' },
                { value: 'movie', label: '电影' },
              ]"
            />
          </label>
          <label class="block space-y-1.5 text-sm">
            <span class="font-medium text-white">上映年份 (可选)</span>
            <Input v-model.number="year" type="number" min="1900" max="2100" placeholder="例如 2024" />
          </label>
        </div>

        <div v-if="mediaType === 'tv'" class="grid grid-cols-2 gap-3 p-3 rounded-xl border border-white/[0.06] bg-zinc-900/40">
          <label class="block space-y-1 text-xs">
            <span class="text-zinc-400">追更季数</span>
            <Input v-model.number="seasonNumber" type="number" min="1" max="100" />
          </label>
          <label class="block space-y-1 text-xs">
            <span class="text-zinc-400">预计总集数</span>
            <Input v-model.number="episodeCount" type="number" min="1" max="1000" />
          </label>
        </div>

        <div>
          <button
            type="button"
            class="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            @click="showAdvanced = !showAdvanced"
          >
            <SlidersHorizontal class="h-3 w-3" />
            <span>{{ showAdvanced ? '收起高级选项' : '高级选项 (可选填 TMDB ID)' }}</span>
          </button>
          <div v-if="showAdvanced" class="mt-2 pt-2 border-t border-white/[0.04]">
            <label class="block space-y-1 text-xs">
              <span class="text-zinc-400">TMDB ID</span>
              <Input v-model.number="tmdbId" type="number" placeholder="例如 94954" />
            </label>
          </div>
        </div>

        <Button type="submit" class="w-full" :disabled="adding">
          {{ adding ? '添加中…' : '立即添加并开始全网找源' }}
        </Button>
      </form>
    </Dialog>
  </div>
</template>
