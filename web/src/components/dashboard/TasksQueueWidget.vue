<script setup lang="ts">
import { computed, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { DownloadCloud } from '@lucide/vue'

import TaskRow from '@/components/domain/TaskRow.vue'
import { useToast } from '@/composables/useToast'
import { tasksApi } from '@/api/transfer'

// 转存队列 widget：与顶栏统计共享 ['tasks'] 查询缓存；失败仅告警
const { toast } = useToast()

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
</script>

<template>
      <!-- 正在进行的转存任务 -->
      <div class="rounded-2xl border border-primary/[0.06] bg-surface-solid/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <DownloadCloud class="h-4 w-4 text-sky-400" />
            <h4 class="text-sm font-semibold text-fg">转存队列</h4>
          </div>
          <RouterLink to="/tasks" class="text-xs text-muted hover:text-fg transition-colors">查看全部任务 →</RouterLink>
        </div>

        <div v-if="!tasks.length" class="py-6 text-center text-xs text-subtle">
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
      </div></template>
