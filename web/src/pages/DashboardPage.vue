<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Activity, AlertTriangle, Clapperboard, ListChecks } from '@lucide/vue'

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
  { label: '媒体总数', value: items.value.length, note: '已纳入追更管理', icon: Clapperboard, tone: 'text-status-transferred' },
  { label: '待补剧集', value: items.value.reduce((total, item) => total + item.missing.length, 0), note: '已播出且尚未入库', icon: AlertTriangle, tone: 'text-status-waiting' },
  { label: '执行任务', value: tasks.value.filter((task) => task.state === 'running').length, note: '当前正在处理', icon: ListChecks, tone: 'text-status-ready' },
  { label: '调度器', value: report.value?.scheduler?.running ? '在线' : '离线', note: '后台任务运行状态', icon: Activity, tone: report.value?.scheduler?.running ? 'text-status-ready' : 'text-status-missing' },
]
</script>

<template>
  <div class="space-y-7">
    <div>
      <p class="font-mono text-[11px] uppercase tracking-[0.2em] text-subtle">Overview</p>
      <h2 class="mt-1 text-2xl font-semibold tracking-tight">追更总览</h2>
      <p class="mt-1 text-sm text-muted">订阅、资源发现与媒体入库状态一览</p>
    </div>

    <div v-if="error" class="rounded-xl border border-status-missing/20 bg-status-missing/10 px-4 py-3 text-sm text-status-missing">
      {{ error }}
    </div>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card v-for="metric in metrics()" :key="metric.label" class="group p-0">
        <CardHeader class="flex-row items-start justify-between pb-2">
          <div class="space-y-1">
            <CardDescription>{{ metric.label }}</CardDescription>
            <p class="tabular-value text-3xl font-semibold tracking-tight">{{ metric.value }}</p>
          </div>
          <span class="grid h-9 w-9 place-items-center rounded-xl border border-border bg-surface-2/70 transition-colors group-hover:bg-surface-3">
            <component :is="metric.icon" class="h-4 w-4" :class="metric.tone" />
          </span>
        </CardHeader>
        <CardContent class="pt-0 text-xs text-subtle">{{ metric.note }}</CardContent>
      </Card>
    </section>

    <section class="space-y-3">
      <div class="flex items-end justify-between">
        <div>
          <h3 class="text-sm font-semibold">自动化流水线</h3>
          <p class="mt-1 text-xs text-muted">从订阅基准到媒体库入库的处理过程</p>
        </div>
        <Badge tone="good" pulse>系统正常</Badge>
      </div>
      <PipelineTracker :active="3" />
    </section>

    <div class="grid gap-4 xl:grid-cols-2">
      <Card class="p-0">
        <CardHeader class="flex-row items-center justify-between">
          <div>
            <CardTitle>追更健康度</CardTitle>
            <CardDescription class="mt-1">近期需要关注的剧集</CardDescription>
          </div>
          <Badge :tone="items.some((item) => item.missing.length) ? 'warn' : 'good'">
            {{ items.length }} 部媒体
          </Badge>
        </CardHeader>
        <CardContent>
          <div v-if="!items.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
            暂无媒体进度数据
          </div>
          <div v-for="media in items.slice(0, 5)" :key="media.media_id" class="flex min-h-12 items-center justify-between gap-4 border-t border-border/70 text-sm">
            <span class="truncate font-medium">{{ media.title }}</span>
            <span class="shrink-0 font-mono text-xs tabular-nums" :class="media.missing.length ? 'text-status-waiting' : 'text-muted'">
              {{ media.missing.length }} 集待补
            </span>
          </div>
          <RouterLink to="/progress" class="mt-2 inline-flex min-h-[44px] items-center text-sm font-medium text-muted transition-colors hover:text-fg">
            查看全部进度 <span class="ml-1">→</span>
          </RouterLink>
        </CardContent>
      </Card>

      <Card class="p-0">
        <CardHeader>
          <CardTitle>系统诊断</CardTitle>
          <CardDescription>服务组件和调度状态</CardDescription>
        </CardHeader>
        <CardContent>
          <pre class="max-h-60 overflow-auto rounded-lg border border-border bg-bg/70 p-4 font-mono text-xs leading-6 text-muted">{{ JSON.stringify(report, null, 2) }}</pre>
        </CardContent>
      </Card>
    </div>

    <section class="space-y-3">
      <div class="flex items-end justify-between">
        <div>
          <h3 class="text-sm font-semibold">最近任务</h3>
          <p class="mt-1 text-xs text-muted">正在处理的转存与整理任务</p>
        </div>
        <RouterLink to="/tasks" class="inline-flex min-h-[44px] items-center text-sm font-medium text-muted hover:text-fg">
          全部任务 →
        </RouterLink>
      </div>
      <div v-if="!tasks.length" class="surface-card px-4 py-8 text-center text-sm text-muted">暂无任务</div>
      <TaskRow
        v-for="task in tasks.slice(0, 3)"
        :key="task.id"
        :task="task"
        @retry="(id) => tasksApi.retry(id).then(() => toast('任务已重新排队', 'success'))"
      />
    </section>
  </div>
</template>
