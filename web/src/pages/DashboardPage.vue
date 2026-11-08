<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  Activity,
  AlertCircle,
  Clapperboard,
  DownloadCloud,
  Film,
  HardDrive,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
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
  try {
    ;[report.value, items.value, tasks.value] = await Promise.all([
      doctorApi.diagnose(),
      progressApi.overview(),
      tasksApi.list(),
    ])
  } catch (cause) {
    console.error(cause)
  } finally {
    loading.value = false
  }
}

onMounted(load)
useEvents((event) => {
  if (event.type === 'task_status' || event.type === 'progress_update') void load()
})

function openMedia(id: number) {
  selectedMediaId.value = id
  drawerOpen.value = true
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
    toast('追更添加成功！系统已开始全网搜源转存', 'success')
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
    <!-- 顶栏精美控制区域 -->
    <div class="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-6">
      <div>
        <div class="flex items-center gap-2.5">
          <h2 class="text-2xl font-bold tracking-tight text-fg">我的追剧</h2>
          <Badge tone="good" pulse>自动监控中</Badge>
        </div>
        <p class="mt-1 text-xs text-muted">
          已关注 <span class="text-fg font-medium">{{ items.length }}</span> 部影视 ·
          待补集数 <span class="font-mono text-amber-400 font-medium">{{ totalMissing() }}</span> 集 ·
          正在转存 <span class="font-mono text-sky-400 font-medium">{{ runningTasks().length }}</span> 个文件
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <RouterLink to="/search">
          <Button variant="outline" size="sm" class="flex items-center gap-1.5">
            <Search class="h-3.5 w-3.5" />
            <span>搜影视</span>
          </Button>
        </RouterLink>
        <Button size="sm" class="flex items-center gap-1.5 shadow-sm shadow-white/10" @click="addOpen = true">
          <Plus class="h-4 w-4" />
          <span>添加追剧</span>
        </Button>
      </div>
    </div>

    <!-- 核心视觉重心：精美影视海报墙（Poster Grid） -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold tracking-tight text-fg flex items-center gap-2">
          <span>追剧清单</span>
          <span class="rounded-full bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-muted">{{ items.length }}</span>
        </h3>
        <span class="text-[11px] text-subtle">点击任意剧集卡片展开季集与网盘文件详情</span>
      </div>

      <!-- 空白占位引导 -->
      <div
        v-if="!items.length && !loading"
        class="rounded-3xl border border-dashed border-border/80 bg-surface/30 p-16 text-center"
      >
        <Film class="mx-auto mb-3 h-10 w-10 text-subtle/50" />
        <h4 class="text-base font-semibold text-fg">追剧清单还是空的</h4>
        <p class="mt-1 text-xs text-muted max-w-sm mx-auto">
          点击右上角「+ 添加追剧」，输入剧名（如：庆余年），系统将全天候自动在全网搜寻资源并存入你的网盘。
        </p>
        <Button size="sm" class="mt-5" @click="addOpen = true">立即添加一部剧</Button>
      </div>

      <!-- 海报卡片墙 -->
      <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
        <MediaPosterCard
          v-for="media in items"
          :key="media.media_id"
          :media="media"
          @select="openMedia"
        />
      </div>
    </section>

    <!-- 底部状态与转存队列横幅（紧凑舒适，不喧宾夺主） -->
    <section class="grid gap-4 lg:grid-cols-12 pt-2">
      <!-- 正在进行的转存任务 -->
      <div class="lg:col-span-8 rounded-2xl border border-border/60 bg-surface/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <DownloadCloud class="h-4 w-4 text-sky-400" />
            <h4 class="text-sm font-semibold text-fg">转存队列</h4>
          </div>
          <RouterLink to="/tasks" class="text-xs text-muted hover:text-fg">查看全部任务 →</RouterLink>
        </div>

        <div v-if="!tasks.length" class="py-5 text-center text-xs text-muted">
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
      <div class="lg:col-span-4 rounded-2xl border border-border/60 bg-surface/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-emerald-400" />
            <h4 class="text-sm font-semibold text-fg">系统运行状态</h4>
          </div>
          <Badge tone="good">正常</Badge>
        </div>

        <div class="space-y-2 pt-1 text-xs">
          <div class="flex items-center justify-between text-muted">
            <span class="flex items-center gap-2">
              <HardDrive class="h-3.5 w-3.5 text-zinc-400" />
              <span>本地 SQLite 存储</span>
            </span>
            <span class="font-mono text-zinc-300">正常</span>
          </div>
          <div class="flex items-center justify-between text-muted border-t border-border/30 pt-2">
            <span class="flex items-center gap-2">
              <RefreshCw class="h-3.5 w-3.5 text-zinc-400" />
              <span>全天候自动轮询</span>
            </span>
            <span class="text-status-ready">30s 巡检</span>
          </div>
          <div class="flex items-center justify-between text-muted border-t border-border/30 pt-2">
            <span class="flex items-center gap-2">
              <Sparkles class="h-3.5 w-3.5 text-zinc-400" />
              <span>网盘账号安全保护</span>
            </span>
            <span class="text-status-ready">Fernet 密保</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 侧滑大抽屉（查看选中的剧集详细文件） -->
    <MediaDrawer
      :open="drawerOpen"
      :media-id="selectedMediaId"
      @close="drawerOpen = false"
    />

    <!-- 添加追剧弹窗 -->
    <Dialog :open="addOpen" title="添加追更订阅" @close="addOpen = false">
      <form class="space-y-4" @submit.prevent="createSubscription">
        <label class="block space-y-1.5 text-sm">
          <span class="font-medium text-fg">影视名称</span>
          <Input v-model="title" required placeholder="例如：庆余年、死侍、边水往事" />
          <span class="text-xs text-muted">直接输入中文或英文片名即可，系统自动匹配</span>
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

        <div v-if="mediaType === 'tv'" class="grid grid-cols-2 gap-3 p-3 rounded-xl border border-border/60 bg-surface-2/30">
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
            class="flex items-center gap-1.5 text-xs text-muted hover:text-fg"
            @click="showAdvanced = !showAdvanced"
          >
            <SlidersHorizontal class="h-3 w-3" />
            <span>{{ showAdvanced ? '收起高级选项' : '高级选项 (可选填 TMDB ID)' }}</span>
          </button>
          <div v-if="showAdvanced" class="mt-2 pt-2 border-t border-border/40">
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
    </Dialog>
  </div>
</template>
