<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { AlertTriangle, Film, RefreshCw, X } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import type { TransferTaskEnriched } from '@/lib/api'
import {
  elapsedLabel,
  mediaTypeLabel,
  providerLabel,
  shortEpisodeLabel,
  taskStateTone,
} from '@/lib/transfer'

const props = defineProps<{
  title: string
  year?: number | null
  type?: string
  posterUrl?: string
  tasks: TransferTaskEnriched[]
}>()

const emit = defineEmits<{ retry: [id: number]; cancel: [id: number] }>()

const posterBroken = ref(false)
const tick = ref(Date.now())
let timer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  timer = setInterval(() => (tick.value = Date.now()), 30000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const STEPS = [
  { keys: ['checking'], label: '校验分享' },
  { keys: ['transferring', 'relaying'], label: '转存中' },
  { keys: ['organizing'], label: '整理入库' },
]

const headline = computed(() => {
  if (props.tasks.some((task) => task.state === 'running')) return { label: '转存中', tone: 'info' as const }
  if (props.tasks.some((task) => task.state === 'queued')) return { label: '排队中', tone: 'default' as const }
  if (props.tasks.some((task) => task.state === 'retry_wait')) return { label: '等待重试', tone: 'warn' as const }
  if (props.tasks.some((task) => task.state === 'dead_letter')) return { label: '有任务失败', tone: 'bad' as const }
  return { label: '待处理', tone: 'muted' as const }
})

const summary = computed(() => {
  const counts = { running: 0, queued: 0, retry_wait: 0, dead_letter: 0 }
  for (const task of props.tasks) {
    if (task.state in counts) counts[task.state as keyof typeof counts] += 1
  }
  const parts: string[] = []
  if (counts.running) parts.push(`转存中 ${counts.running}`)
  if (counts.queued) parts.push(`排队 ${counts.queued}`)
  if (counts.retry_wait) parts.push(`等待重试 ${counts.retry_wait}`)
  if (counts.dead_letter) parts.push(`失败 ${counts.dead_letter}`)
  return parts.join(' · ') || `共 ${props.tasks.length} 个任务`
})

function stepIndex(task: TransferTaskEnriched): number {
  const stage = task.stage || ''
  const index = STEPS.findIndex((step) => step.keys.includes(stage))
  if (index >= 0) return index
  return task.state === 'running' ? 0 : 0
}

function stageText(task: TransferTaskEnriched): string {
  if (task.state === 'queued') return '排队中'
  if (task.state === 'retry_wait') return '等待重试'
  if (task.state === 'dead_letter') return '转存失败'
  return task.stage_label || STEPS[stepIndex(task)].label
}

function duration(task: TransferTaskEnriched): string {
  void tick.value
  return elapsedLabel(task.created_at)
}
</script>

<template>
  <article
    class="group relative overflow-hidden rounded-2xl border border-white/[0.07] bg-surface/40 p-4 transition-colors hover:border-white/[0.12]"
  >
    <div
      class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent"
    />

    <div class="flex gap-4">
      <!-- 海报 -->
      <div
        class="relative h-[68px] w-[48px] shrink-0 overflow-hidden rounded-lg bg-gradient-to-br from-zinc-800 to-zinc-900 ring-1 ring-white/[0.06]"
      >
        <img
          v-if="posterUrl && !posterBroken"
          :src="posterUrl"
          alt=""
          class="h-full w-full object-cover"
          loading="lazy"
          @error="posterBroken = true"
        />
        <Film v-else class="absolute inset-0 m-auto h-5 w-5 text-zinc-600" />
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate text-sm font-semibold tracking-tight text-fg">
              {{ title || '手动转存' }}
              <span v-if="year" class="ml-1 text-[11px] font-normal text-subtle">{{ year }}</span>
            </h3>
            <p class="mt-0.5 truncate text-[11px] text-subtle">
              {{ mediaTypeLabel(type) }} · {{ summary }}
            </p>
          </div>
          <Badge :tone="headline.tone" :pulse="headline.tone === 'info'">{{ headline.label }}</Badge>
        </div>

        <ul class="mt-3 space-y-2">
          <li
            v-for="task in tasks"
            :key="task.id"
            class="rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2.5"
          >
            <div class="flex items-start gap-2">
              <span
                v-if="task.media_type !== 'movie' && shortEpisodeLabel(task.season, task.episode)"
                class="mt-[3px] shrink-0 rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-zinc-300"
              >
                {{ shortEpisodeLabel(task.season, task.episode) }}
              </span>
              <span
                class="line-clamp-2 min-w-0 flex-1 text-xs leading-5 text-zinc-200"
                :title="task.display_name"
              >
                {{ task.display_name }}
              </span>
            </div>

            <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
              <Badge tone="muted">{{ providerLabel(task.provider) }}</Badge>
              <Badge :tone="taskStateTone(task.state)" :pulse="task.state === 'running'">
                {{ stageText(task) }}
              </Badge>
              <span
                v-if="task.quality_bucket"
                class="font-mono text-[10px] uppercase tracking-wide text-subtle"
              >
                {{ task.quality_bucket }}
              </span>
            </div>

            <!-- 阶段轨道：只表达走到哪一步，不伪造百分比 -->
            <div v-if="task.state === 'running'" class="mt-2.5 flex items-center gap-1.5">
              <template v-for="(step, index) in STEPS" :key="step.label">
                <div
                  class="h-1 w-7 rounded-full transition-colors"
                  :class="index <= stepIndex(task) ? 'bg-sky-400/60' : 'bg-white/[0.06]'"
                />
              </template>
            </div>

            <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-subtle">
              <span class="inline-flex items-center gap-1">
                <RefreshCw class="h-3 w-3" />
                第 {{ Math.max(1, task.attempt) }} 次尝试
              </span>
              <span>{{ duration(task) }}前开始</span>
              <span v-if="task.next_retry_at" class="text-amber-300/80">
                下次 {{ new Date(task.next_retry_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
              </span>
              <span class="ml-auto flex items-center gap-1.5">
                <Button
                  v-if="task.state === 'retry_wait' || task.state === 'dead_letter'"
                  variant="ghost"
                  size="sm"
                  @click="emit('retry', task.id)"
                >
                  立即重试
                </Button>
                <Button
                  v-if="task.state === 'queued'"
                  variant="ghost"
                  size="sm"
                  class="text-zinc-400 hover:text-rose-300"
                  @click="emit('cancel', task.id)"
                >
                  <X class="h-3.5 w-3.5" />
                  取消
                </Button>
              </span>
            </div>

            <div
              v-if="task.failure_label"
              class="mt-2 flex items-start gap-1.5 rounded-lg border border-rose-500/15 bg-rose-500/[0.06] px-2.5 py-1.5"
              :title="task.failure_detail || task.last_error || ''"
            >
              <AlertTriangle class="mt-0.5 h-3 w-3 shrink-0 text-rose-400" />
              <p class="truncate text-[11px] leading-4 text-rose-200/80">
                {{ task.failure_label }}
              </p>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </article>
</template>
