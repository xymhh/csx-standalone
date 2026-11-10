<script setup lang="ts">
import { Clapperboard } from '@lucide/vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'

// 与 DramaSection 共享同一份 form（transfer 部分字段）
const form = defineModel<Record<string, any>>('form', { required: true })
</script>

<template>
  <!-- 卡片 B: 转存与画质门槛 -->
  <div class="apple-glass rounded-2xl p-5 space-y-4">
    <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
      <Clapperboard class="h-4 w-4 text-indigo-400" />
      <h3 class="text-sm font-semibold text-fg">网盘转存与洗版</h3>
    </div>

    <div class="space-y-3.5 text-xs">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">首选转存网盘</p>
          <p class="text-[11px] text-subtle">多源并存时优先存入此网盘</p>
        </div>
        <div class="w-36">
          <Select
            v-model="form.default_drive"
            :options="[
              { value: 'quark', label: '夸克网盘' },
              { value: '115', label: '115 网盘' },
            ]"
          />
        </div>
      </div>

      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">最低画质门槛</p>
          <p class="text-[11px] text-subtle">低于此规格资源直接忽略</p>
        </div>
        <div class="w-36">
          <Select
            v-model="form.min_quality"
            :options="[
              { value: 'sd', label: '720p 标清' },
              { value: 'hd', label: '1080p 高清' },
              { value: '4k', label: '4K 超高清' },
            ]"
          />
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div>
          <p class="font-medium text-fg">画质自动洗版</p>
          <p class="text-[11px] text-subtle">搜寻到更高画质时自动替换旧版</p>
        </div>
        <Switch v-model="form.enable_cloud_upgrade" />
      </div>
    </div>
  </div>
</template>
