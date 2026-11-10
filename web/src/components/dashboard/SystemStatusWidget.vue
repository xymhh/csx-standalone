<script setup lang="ts">
import { watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { Activity, HardDrive, RefreshCw, Sparkles } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import { doctorApi } from '@/api/settings'

// 系统状态 widget：卡片内容为静态健康指标；挂载时触发一次后端自检（失败仅告警，与拆分前一致）
const doctorQuery = useQuery({
  queryKey: ['doctor'],
  queryFn: () => doctorApi.diagnose(),
})
watch(
  () => doctorQuery.error.value,
  (cause) => {
    if (cause) console.warn('系统自检失败', cause)
  },
)
</script>

<template>
      <!-- 系统健康状态指标 -->
      <div class="rounded-2xl border border-primary/[0.06] bg-surface-solid/40 p-5 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-emerald-400" />
            <h4 class="text-sm font-semibold text-fg">系统运行状态</h4>
          </div>
          <Badge tone="good">正常</Badge>
        </div>

        <div class="space-y-2.5 pt-1 text-xs">
          <div class="flex items-center justify-between text-muted">
            <span class="flex items-center gap-2">
              <HardDrive class="h-3.5 w-3.5 text-subtle" />
              <span>本地 SQLite 存储</span>
            </span>
            <span class="font-mono text-fg-2">正常</span>
          </div>
          <div class="flex items-center justify-between text-muted border-t border-primary/[0.04] pt-2.5">
            <span class="flex items-center gap-2">
              <RefreshCw class="h-3.5 w-3.5 text-subtle" />
              <span>全天候自动轮询</span>
            </span>
            <span class="text-emerald-400 font-medium">30s 巡检</span>
          </div>
          <div class="flex items-center justify-between text-muted border-t border-primary/[0.04] pt-2.5">
            <span class="flex items-center gap-2">
              <Sparkles class="h-3.5 w-3.5 text-subtle" />
              <span>网盘账号安全保护</span>
            </span>
            <span class="text-emerald-400 font-medium">Fernet 密保</span>
          </div>
        </div>
      </div>
</template>
