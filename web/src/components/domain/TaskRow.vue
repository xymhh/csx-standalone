<script setup lang="ts">
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import type { Task } from '@/api/transfer'

defineProps<{ task: Task }>()
defineEmits<{ retry: [id: number]; cancel: [id: number] }>()

const stateMap: Record<string, { label: string; tone: 'good' | 'bad' | 'warn' | 'info' | 'muted' }> = {
  succeeded: { label: '已完成', tone: 'good' },
  running: { label: '正在转存', tone: 'info' },
  queued: { label: '排队中', tone: 'muted' },
  retry_wait: { label: '等待重试', tone: 'warn' },
  dead_letter: { label: '转存失败', tone: 'bad' },
  cancelled: { label: '已取消', tone: 'muted' },
}
</script>

<template>
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-border/50 bg-surface/30 p-3.5 transition-colors hover:border-border/80">
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-fg">任务 #{{ task.id }}</span>
        <Badge :tone="stateMap[task.state]?.tone ?? 'muted'" :pulse="task.state === 'running'">
          {{ stateMap[task.state]?.label ?? task.state }}
        </Badge>
        <span v-if="task.attempt > 1" class="font-mono text-[11px] text-subtle">
          第 {{ task.attempt }} 次尝试
        </span>
      </div>
      <p class="mt-1 truncate font-mono text-[11px] text-subtle" :title="task.idempotency_key">
        {{ task.idempotency_key }}
      </p>
      <p v-if="task.last_error" class="mt-1 text-xs text-status-missing">
        {{ task.last_error }}
      </p>
    </div>

    <div class="flex shrink-0 items-center gap-2">
      <Button
        v-if="task.state === 'dead_letter' || task.state === 'retry_wait'"
        variant="outline"
        size="sm"
        @click="$emit('retry', task.id)"
      >
        立即重试
      </Button>
      <Button
        v-if="task.state === 'queued'"
        variant="ghost"
        size="sm"
        @click="$emit('cancel', task.id)"
      >
        取消
      </Button>
    </div>
  </div>
</template>
