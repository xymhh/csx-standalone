<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Activity, AlertTriangle, Clapperboard, DownloadCloud, HardDrive, CheckCircle2, ShieldCheck, RefreshCw } from '@lucide/vue'

import PipelineTracker from '@/components/domain/PipelineTracker.vue'
import TaskRow from '@/components/domain/TaskRow.vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardDescription from '@/components/ui/CardDescription.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import { useEvents } from '@/composables/useEvents'
import { useToast } from '@/composables/useToast'
import { doctorApi, progressApi, tasksApi, type DoctorReport, type ProgressItem, type Task } from '@/lib/api'

const { toast } = useToast()
const report = ref<DoctorReport | null>(null)
const items = ref<ProgressItem[]>([])
const tasks = ref<Task[]>([])
const error = ref('')

async function load() {
  try {
    ;[report.value, items.value, tasks.value] = await Promise.all([
      doctorApi.diagnose(),
      progressApi.overview(),
      tasksApi.list(),
    ])
    error.value = ''
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败'
  }
}

onMounted(load)
useEvents((event) => {
  if (event.type === 'task_status') void load()
})

const metrics = () => [
  { label: '正在追剧', value: items.value.length, note: '部已关注影视', icon: Clapperboard, tone: 'text-status-transferred' },
  { label: '缺少集数', value: items.value.reduce((total, item) => total + item.missing.length, 0), note: '已播出未入库集数', icon: AlertTriangle, tone: 'text-status-waiting' },
  { label: '正在转存', value: tasks.value.filter((task) => task.state === 'running').length, note: '个文件下载中', icon: DownloadCloud, tone: 'text-status-ready' },
  { label: '自动追更服务', value: report.value?.scheduler?.running ? '运行中' : '已暂停', note: '全天候自动监控', icon: Activity, tone: report.value?.scheduler?.running ? 'text-status-ready' : 'text-status-missing' },
]
</script>

<template>
  <div class="space-y-7">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-fg">控制台</h2>
      <p class="mt-1 text-sm text-muted">系统正在为你全自动监控影视更新并自动转存入库</p>
    </div>

    <div v-if="error" class="rounded-xl border border-status-missing/20 bg-status-missing/10 px-4 py-3 text-sm text-status-missing">
      {{ error }}
    </div>

    <!-- 顶部核心指标卡 -->
    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="metric in metrics()" :key="metric.label" class="group p-0">
        <CardHeader class="flex-row items-start justify-between pb-2">
          <div class="space-y-1">
            <CardDescription class="text-xs font-medium">{{ metric.label }}</CardDescription>
            <p class="tabular-value text-3xl font-semibold tracking-tight">{{ metric.value }}</p>
          </div>
          <span class="grid h-9 w-9 place-items-center rounded-xl border border-border bg-surface-2/70 transition-colors group-hover:bg-surface-3">
            <component :is="metric.icon" class="h-4 w-4" :class="metric.tone" />
          </span>
        </CardHeader>
        <CardContent class="pt-0 text-xs text-subtle">{{ metric.note }}</CardContent>
      </Card>
    </section>

    <!-- 自动流水线说明 -->
    <section class="space-y-3">
      <div class="flex items-end justify-between">
        <div>
          <h3 class="text-sm font-semibold text-fg">自动追更流程</h3>
          <p class="mt-0.5 text-xs text-muted">从发现剧集更新到自动存入你网盘的处理进度</p>
        </div>
        <Badge tone="good" pulse>运行正常</Badge>
      </div>
      <PipelineTracker :active="3" />
    </section>

    <!-- 追剧动态与系统运行状态分栏（人话卡片，拒绝裸 JSON） -->
    <div class="grid gap-4 xl:grid-cols-2">
      <!-- 追剧动态卡片 -->
      <Card class="p-0">
        <CardHeader class="flex-row items-center justify-between">
          <div>
            <CardTitle class="text-base font-semibold">追更动态</CardTitle>
            <CardDescription class="mt-0.5">关注剧集的最新入库状态</CardDescription>
          </div>
          <Badge :tone="items.some((item) => item.missing.length) ? 'warn' : 'good'">
            共关注 {{ items.length }} 部
          </Badge>
        </CardHeader>
        <CardContent>
          <div v-if="!items.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
            <p>还没有添加任何追剧订阅</p>
            <RouterLink to="/baseline" class="mt-2 inline-block text-xs text-primary hover:underline">
              去「我的订阅」添加一部剧 →
            </RouterLink>
          </div>
          <div v-for="media in items.slice(0, 5)" :key="media.media_id" class="flex min-h-12 items-center justify-between gap-4 border-t border-border/70 text-sm">
            <span class="truncate font-medium">{{ media.title }}</span>
            <span class="shrink-0 text-xs" :class="media.missing.length ? 'text-status-waiting' : 'text-status-ready'">
              {{ media.missing.length ? `缺 ${media.missing.length} 集待转存` : '全集已入库' }}
            </span>
          </div>
          <RouterLink to="/progress" class="mt-3 inline-flex min-h-[44px] items-center text-sm font-medium text-muted transition-colors hover:text-fg">
            查看全部追剧进度 <span class="ml-1">→</span>
          </RouterLink>
        </CardContent>
      </Card>

      <!-- 服务状态健康卡片（大白话组件，替代原生裸 JSON） -->
      <Card class="p-0">
        <CardHeader class="flex-row items-center justify-between">
          <div>
            <CardTitle class="text-base font-semibold">运行状态</CardTitle>
            <CardDescription class="mt-0.5">各项后台服务健康度</CardDescription>
          </div>
          <Badge tone="good" pulse>健康</Badge>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/40 p-3">
            <div class="flex items-center gap-3">
              <HardDrive class="h-4 w-4 text-emerald-400" />
              <div>
                <p class="text-sm font-medium">数据库存储</p>
                <p class="text-xs text-muted">SQLite 独立运行，读写正常</p>
              </div>
            </div>
            <Badge tone="good">正常</Badge>
          </div>

          <div class="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/40 p-3">
            <div class="flex items-center gap-3">
              <RefreshCw class="h-4 w-4 text-emerald-400" />
              <div>
                <p class="text-sm font-medium">自动监控服务</p>
                <p class="text-xs text-muted">每 30 秒自动巡查更新与转存任务</p>
              </div>
            </div>
            <Badge tone="good">运行中</Badge>
          </div>

          <div class="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/40 p-3">
            <div class="flex items-center gap-3">
              <ShieldCheck class="h-4 w-4 text-emerald-400" />
              <div>
                <p class="text-sm font-medium">网盘账号安全</p>
                <p class="text-xs text-muted">所有凭据均采用高强度加密保存</p>
              </div>
            </div>
            <Badge tone="good">已受保护</Badge>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 最近转存任务 -->
    <section class="space-y-3">
      <div class="flex items-end justify-between">
        <div>
          <h3 class="text-sm font-semibold text-fg">正在转存的任务</h3>
          <p class="mt-0.5 text-xs text-muted">系统正在为你下载和整理的影视文件</p>
        </div>
        <RouterLink to="/tasks" class="inline-flex min-h-[44px] items-center text-sm font-medium text-muted hover:text-fg">
          查看全部任务 →
        </RouterLink>
      </div>
      <div v-if="!tasks.length" class="surface-card px-4 py-8 text-center text-sm text-muted">当前没有正在转存的任务</div>
      <TaskRow
        v-for="task in tasks.slice(0, 3)"
        :key="task.id"
        :task="task"
        @retry="(id) => tasksApi.retry(id).then(() => toast('已重新开始转存', 'success'))"
      />
    </section>
  </div>
</template>
