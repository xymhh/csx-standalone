<script setup lang="ts">
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import type { Task } from '@/lib/api'

defineProps<{ task: Task }>()
defineEmits<{ retry: [id: number]; cancel: [id: number] }>()
</script>

<template>
  <article class="surface-card flex flex-col gap-4 p-4 transition-colors hover:border-primary/15 sm:flex-row sm:items-center sm:p-5">
    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-center gap-2">
        <strong class="font-semibold tracking-tight">任务 <span class="font-mono tabular-nums">#{{ task.id }}</span></strong>
        <Badge :tone="task.state === 'succeeded' ? 'good' : task.state === 'dead_letter' ? 'bad' : task.state === 'retry_wait' ? 'warn' : task.state === 'running' ? 'info' : 'muted'" :pulse="task.state === 'running'">
          {{ task.state }}
        </Badge>
      </div>
      <p class="mt-2 truncate font-mono text-xs text-muted" :title="task.idempotency_key">
        {{ task.idempotency_key }}
      </p>
      <p v-if="task.last_error" class="mt-2 text-sm text-status-missing">{{ task.last_error }}</p>
      <p v-if="task.next_retry_at" class="mt-1 text-xs text-subtle">
        下次重试：{{ new Date(task.next_retry_at).toLocaleString() }}
      </p>
    </div>
    <div class="flex gap-2">
      <Button
        v-if="task.state === 'dead_letter' || task.state === 'retry_wait'"
        variant="outline"
        size="sm"
        @click="$emit('retry', task.id)"
      >
        提前重试
      </Button>
      <Button v-if="task.state === 'queued'" variant="outline" size="sm" @click="$emit('cancel', task.id)">
        取消排队
      </Button>
    </div>
  </article>
</template>
