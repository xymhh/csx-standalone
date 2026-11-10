<script setup lang="ts">
import type { Component } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'

import PosterWallWidget from '@/components/dashboard/PosterWallWidget.vue'
import SystemStatusWidget from '@/components/dashboard/SystemStatusWidget.vue'
import TasksQueueWidget from '@/components/dashboard/TasksQueueWidget.vue'
import { useEvents } from '@/composables/useEvents'

// 仪表盘 widget 注册表：页面只负责网格编排，各 widget 自带数据查询与交互状态
interface DashboardWidget {
  id: string
  component: Component
  /** 12 栅格中的跨度；12 表示整行独立区块 */
  span: 4 | 8 | 12
}

const widgets: DashboardWidget[] = [
  { id: 'poster-wall', component: PosterWallWidget, span: 12 },
  { id: 'task-queue', component: TasksQueueWidget, span: 8 },
  { id: 'system-status', component: SystemStatusWidget, span: 4 },
]

const fullWidthWidgets = widgets.filter((widget) => widget.span >= 12)
const gridWidgets = widgets.filter((widget) => widget.span < 12)

// 静态映射保证 Tailwind 能扫描到完整的栅格类名
const SPAN_CLASS: Record<number, string> = {
  4: 'lg:col-span-4',
  8: 'lg:col-span-8',
  12: 'lg:col-span-12',
}

// SSE 实时事件：失效各 widget 共享的查询缓存，由各 widget 自行重新拉取
const queryClient = useQueryClient()
useEvents((event) => {
  if (event.type === 'task_status' || event.type === 'progress_update') {
    void queryClient.invalidateQueries({ queryKey: ['progress', 'overview'] })
    void queryClient.invalidateQueries({ queryKey: ['tasks'] })
    void queryClient.invalidateQueries({ queryKey: ['doctor'] })
  }
})
</script>

<template>
  <div class="space-y-8">
    <component :is="widget.component" v-for="widget in fullWidthWidgets" :key="widget.id" />

    <!-- 底部状态与转存队列横幅 -->
    <section class="grid gap-5 lg:grid-cols-12 pt-2">
      <component
        :is="widget.component"
        v-for="widget in gridWidgets"
        :key="widget.id"
        :class="SPAN_CLASS[widget.span]"
      />
    </section>
  </div>
</template>
