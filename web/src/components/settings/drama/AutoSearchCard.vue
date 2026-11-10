<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Radar, RefreshCw } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import { useToast } from '@/composables/useToast'
import { type AutoSearchSettings, autoSearchApi } from '@/api/autoSearch'

const { toast } = useToast()

const autoCfg = ref<AutoSearchSettings>({
  enabled: false,
  interval_hours: 6,
  auto_transfer: true,
  max_per_round: 10,
  per_subscription_limit: 20,
})
const autoSaving = ref(false)
const autoRunning = ref(false)

async function loadAutoSearch() {
  try {
    autoCfg.value = await autoSearchApi.settings()
  } catch {
    /* 老后端无此接口时静默 */
  }
}

async function saveAutoSearch() {
  autoSaving.value = true
  try {
    autoCfg.value = await autoSearchApi.save({
      enabled: autoCfg.value.enabled,
      interval_hours: Number(autoCfg.value.interval_hours),
      auto_transfer: autoCfg.value.auto_transfer,
      max_per_round: Number(autoCfg.value.max_per_round),
      per_subscription_limit: Number(autoCfg.value.per_subscription_limit),
    })
    toast(autoCfg.value.enabled ? '自动搜源已开启' : '自动搜源已关闭', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    autoSaving.value = false
  }
}

async function runAutoSearchNow() {
  autoRunning.value = true
  try {
    const response = await autoSearchApi.run({ force: true })
    const result = response.result
    const count = result.total ?? result.processed?.length ?? 0
    const taskCount = Array.isArray(result.tasks) ? result.tasks.length : Number(result.tasks ?? 0)
    toast(`已跑 ${count} 部订阅：新候选 ${result.candidates ?? 0} 个，新建转存 ${taskCount} 个`, 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '触发失败', 'error')
  } finally {
    autoRunning.value = false
  }
}

onMounted(() => {
  void loadAutoSearch()
})
</script>

<template>
  <!-- 卡片 A2: 订阅自动搜源 -->
  <div class="apple-glass rounded-2xl p-5 space-y-4">
    <div class="flex items-center gap-2 border-b border-primary/[0.06] pb-3">
      <Radar class="h-4 w-4 text-emerald-400" />
      <h3 class="text-sm font-semibold text-fg">订阅自动搜源</h3>
    </div>

    <div class="space-y-3.5 text-xs">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">自动搜源总开关</p>
          <p class="text-[11px] text-subtle">开启后按间隔为每部追剧搜渠道，命中缺失集自动转存</p>
        </div>
        <Switch v-model="autoCfg.enabled" />
      </div>

      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">搜源间隔</p>
          <p class="text-[11px] text-subtle">同一部剧多久搜一轮</p>
        </div>
        <Select
          :model-value="String(autoCfg.interval_hours)"
          class="w-28"
          :options="[{ value: '1', label: '1 小时' }, { value: '3', label: '3 小时' }, { value: '6', label: '6 小时' }, { value: '12', label: '12 小时' }, { value: '24', label: '24 小时' }]"
          @update:model-value="(v: string) => (autoCfg.interval_hours = Number(v))"
        />
      </div>

      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">每轮最多订阅</p>
          <p class="text-[11px] text-subtle">防止一次搜太多触发渠道限流</p>
        </div>
        <Select
          :model-value="String(autoCfg.max_per_round)"
          class="w-28"
          :options="[{ value: '5', label: '5 部' }, { value: '10', label: '10 部' }, { value: '20', label: '20 部' }, { value: '50', label: '50 部' }]"
          @update:model-value="(v: string) => (autoCfg.max_per_round = Number(v))"
        />
      </div>

      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">每部候选上限</p>
          <p class="text-[11px] text-subtle">每次向渠道要多少条结果</p>
        </div>
        <Select
          :model-value="String(autoCfg.per_subscription_limit)"
          class="w-28"
          :options="[{ value: '10', label: '10 条' }, { value: '20', label: '20 条' }, { value: '30', label: '30 条' }, { value: '50', label: '50 条' }]"
          @update:model-value="(v: string) => (autoCfg.per_subscription_limit = Number(v))"
        />
      </div>

      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-fg">命中即自动转存</p>
          <p class="text-[11px] text-subtle">关闭时只入「待选资源」，由你手动确认</p>
        </div>
        <Switch v-model="autoCfg.auto_transfer" />
      </div>

      <div class="flex items-center gap-2 pt-1">
        <Button size="sm" :disabled="autoSaving" @click="saveAutoSearch">
          {{ autoSaving ? '保存中…' : '保存设置' }}
        </Button>
        <Button variant="outline" size="sm" :disabled="autoRunning" @click="runAutoSearchNow">
          <RefreshCw class="mr-1.5 h-3.5 w-3.5" :class="autoRunning ? 'animate-spin' : ''" />
          {{ autoRunning ? '搜索中…' : '立即跑一轮' }}
        </Button>
      </div>
    </div>
  </div>
</template>
