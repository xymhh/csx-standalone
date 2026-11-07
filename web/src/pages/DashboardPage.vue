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
  ShieldCheck,
} from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import TaskRow from '@/components/domain/TaskRow.vue'
import { useEvents } from '@/composables/useEvents'
import { useToast } from '@/composables/useToast'
import {
  doctorApi,
  progressApi,
  tasksApi,
  type DoctorReport,
  type ProgressItem,
  type Task,
} from '@/lib/api'

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

const totalMissing = () => items.value.reduce((total, item) => total + item.missing.length, 0)
const runningTasksCount = () => tasks.value.filter((t) => t.state === 'running').length
</script>

<template>
  <div class="space-y-6">
    <!-- 顶栏标题与操作 -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold tracking-tight text-fg">控制台</h2>
        <p class="mt-0.5 text-xs text-muted">全天候自动监控影视更新并自动存入网盘</p>
      </div>
      <div class="flex items-center gap-2">
        <RouterLink to="/baseline">
          <Button size="sm" class="flex items-center gap-1.5 shadow-sm">
            <Plus class="h-3.5 w-3.5" />
            <span>添加追剧</span>
          </Button>
        </RouterLink>
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-lg border border-status-missing/20 bg-status-missing/10 px-4 py-3 text-xs text-status-missing"
    >
      {{ error }}
    </div>

    <!-- 4 个轻量指标卡 -->
    <section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border">
        <div class="flex items-center justify-between text-subtle">
          <span class="text-xs font-medium">正在追剧</span>
          <Clapperboard class="h-4 w-4" />
        </div>
        <p class="mt-2 font-mono text-2xl font-semibold tracking-tight text-fg">{{ items.length }}</p>
        <p class="mt-1 text-[11px] text-subtle">已关注部数</p>
      </div>

      <div class="rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border">
        <div class="flex items-center justify-between text-subtle">
          <span class="text-xs font-medium">待补集数</span>
          <AlertCircle class="h-4 w-4" :class="totalMissing() ? 'text-status-waiting' : ''" />
        </div>
        <p class="mt-2 font-mono text-2xl font-semibold tracking-tight" :class="totalMissing() ? 'text-status-waiting' : 'text-fg'">
          {{ totalMissing() }}
        </p>
        <p class="mt-1 text-[11px] text-subtle">未入库缺集</p>
      </div>

      <div class="rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border">
        <div class="flex items-center justify-between text-subtle">
          <span class="text-xs font-medium">正在转存</span>
          <DownloadCloud class="h-4 w-4" :class="runningTasksCount() ? 'text-status-ready' : ''" />
        </div>
        <p class="mt-2 font-mono text-2xl font-semibold tracking-tight text-fg">{{ runningTasksCount() }}</p>
        <p class="mt-1 text-[11px] text-subtle">活跃任务数</p>
      </div>

      <div class="rounded-xl border border-border/60 bg-surface/40 p-4 transition-colors hover:border-border">
        <div class="flex items-center justify-between text-subtle">
          <span class="text-xs font-medium">监控服务</span>
          <Activity class="h-4 w-4 text-status-ready" />
        </div>
        <p class="mt-2 text-2xl font-semibold tracking-tight text-status-ready">
          {{ report?.scheduler?.running ? '运行中' : '已暂停' }}
        </p>
        <p class="mt-1 text-[11px] text-subtle">后台轮询</p>
      </div>
    </section>

    <!-- 主体区域：左 7 分 追剧动态，右 5 分 转存与服务 -->
    <div class="grid gap-6 lg:grid-cols-12">
      <!-- 左栏：追更动态 -->
      <section class="lg:col-span-7 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-fg">追更动态</h3>
          <RouterLink to="/progress" class="text-xs text-muted hover:text-fg">全部进度 →</RouterLink>
        </div>

        <div class="rounded-xl border border-border/60 bg-surface/40 p-4">
          <div v-if="!items.length" class="py-12 text-center">
            <Film class="mx-auto mb-2 h-7 w-7 text-subtle/50" />
            <p class="text-xs text-muted">当前还没有添加任何追更影视</p>
            <RouterLink to="/baseline" class="mt-3 inline-block">
              <Button variant="outline" size="sm">去添加第一部剧</Button>
            </RouterLink>
          </div>

          <div v-else class="divide-y divide-border/40">
            <div
              v-for="media in items.slice(0, 6)"
              :key="media.media_id"
              class="flex items-center justify-between py-2.5 first:pt-0 last:pb-0"
            >
              <div class="min-w-0 flex-1 pr-4">
                <p class="truncate text-xs font-medium text-fg">{{ media.title }}</p>
                <div class="mt-1 flex items-center gap-2">
                  <div class="h-1.5 w-24 overflow-hidden rounded-full bg-surface-2">
                    <div
                      class="h-full bg-status-ready"
                      :style="{
                        width: media.aired_count ? `${Math.round((media.owned_count / media.aired_count) * 100)}%` : '0%',
                      }"
                    />
                  </div>
                  <span class="font-mono text-[11px] text-subtle">
                    {{ media.owned_count }} / {{ media.aired_count }}
                  </span>
                </div>
              </div>
              <Badge :tone="media.missing.length ? 'warn' : 'good'">
                {{ media.missing.length ? `缺 ${media.missing.length} 集` : '已齐' }}
              </Badge>
            </div>
          </div>
        </div>
      </section>

      <!-- 右栏：正在转存与系统状态 -->
      <section class="lg:col-span-5 space-y-5">
        <!-- 任务列表 -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-fg">转存队列</h3>
            <RouterLink to="/tasks" class="text-xs text-muted hover:text-fg">全部任务 →</RouterLink>
          </div>

          <div class="rounded-xl border border-border/60 bg-surface/40 p-4">
            <div v-if="!tasks.length" class="py-6 text-center text-xs text-muted">
              暂无正在处理的任务
            </div>
            <div v-else class="space-y-2">
              <TaskRow
                v-for="task in tasks.slice(0, 3)"
                :key="task.id"
                :task="task"
                @retry="(id) => tasksApi.retry(id).then(() => toast('已重新排队', 'success'))"
              />
            </div>
          </div>
        </div>

        <!-- 极简系统健康指示 -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold text-fg">系统服务</h3>
          <div class="rounded-xl border border-border/60 bg-surface/40 p-3.5 space-y-2.5 text-xs">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-muted">
                <HardDrive class="h-3.5 w-3.5 text-status-ready" />
                <span>SQLite 数据库</span>
              </div>
              <span class="text-status-ready font-medium">正常</span>
            </div>
            <div class="flex items-center justify-between border-t border-border/30 pt-2.5">
              <div class="flex items-center gap-2 text-muted">
                <RefreshCw class="h-3.5 w-3.5 text-status-ready" />
                <span>后台定时轮询</span>
              </div>
              <span class="text-status-ready font-medium">运行中</span>
            </div>
            <div class="flex items-center justify-between border-t border-border/30 pt-2.5">
              <div class="flex items-center gap-2 text-muted">
                <ShieldCheck class="h-3.5 w-3.5 text-status-ready" />
                <span>网盘凭据加密</span>
              </div>
              <span class="text-status-ready font-medium">Fernet 保护</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
