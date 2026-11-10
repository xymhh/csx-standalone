<script setup lang="ts">
import { ref } from 'vue'

import Button from '@/components/ui/Button.vue'
import Tabs from '@/components/ui/Tabs.vue'
import AccountsSection from '@/components/settings/AccountsSection.vue'
import ChartsSection from '@/components/settings/ChartsSection.vue'
import DramaSection from '@/components/settings/DramaSection.vue'
import PlaybackSection from '@/components/settings/PlaybackSection.vue'
import SourcesSection from '@/components/settings/SourcesSection.vue'
import SystemSection from '@/components/settings/SystemSection.vue'
import { useToast } from '@/composables/useToast'
import { settingsApi } from '@/api/settings'

const navItems = [
  { value: 'accounts', label: '网盘账号' },
  { value: 'drama', label: '追剧与规则' },
  { value: 'charts', label: '榜单自动订阅' },
  { value: 'sources', label: '搜索渠道 (15)' },
  { value: 'playback', label: '播放与整理' },
  { value: 'system', label: '通知与高级' },
]

const currentNav = ref('accounts')
const { toast } = useToast()
const saving = ref(false)

const dramaRef = ref<InstanceType<typeof DramaSection> | null>(null)
const chartsRef = ref<InstanceType<typeof ChartsSection> | null>(null)
const sourcesRef = ref<(InstanceType<typeof SourcesSection> & { saveSources: () => Promise<void> }) | null>(null)
const playbackRef = ref<InstanceType<typeof PlaybackSection> | null>(null)
const systemRef = ref<InstanceType<typeof SystemSection> | null>(null)

// 全局保存：各区块通过 collect* 提供自己那份载荷，父级只负责编排与提示（语义与拆分前一致）
async function saveAll() {
  saving.value = true
  try {
    if (currentNav.value === 'sources') {
      await sourcesRef.value?.saveSources()
      return
    }

    let namingError = ''
    const namingSave = (dramaRef.value?.saveNaming() ?? Promise.resolve('')).then((err) => {
      namingError = err
    })

    await Promise.all([
      settingsApi.updateSection('baseline', {
        ...dramaRef.value?.collectBaseline(),
        ...chartsRef.value?.collectBaseline(),
      }),
      settingsApi.updateSection('transfer', {
        ...dramaRef.value?.collectTransfer(),
        ...playbackRef.value?.collectTransfer(),
      }),
      settingsApi.updateSection('strm', playbackRef.value?.collectStrm() ?? {}),
      settingsApi.updateSection('notify', systemRef.value?.collectNotify() ?? {}),
      settingsApi.updateSection('advanced', systemRef.value?.collectAdvanced() ?? {}),
      settingsApi.updateSection('category', playbackRef.value?.collectCategory() ?? {}),
      namingSave,
    ])

    if (namingError) {
      toast(`其余设置已保存；重命名模板未保存：${namingError}`, 'error')
    } else {
      toast('设置保存成功', 'success')
    }
    void systemRef.value?.refreshTgStatus()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6 max-w-6xl">
    <!-- 顶部极简标题与全局操作 -->
    <header class="flex items-center justify-between gap-4 border-b border-primary/[0.08] pb-4">
      <div>
        <h2 class="text-xl font-bold tracking-tight text-fg">系统设置</h2>
        <p class="text-xs text-muted mt-0.5">调控自动化追更、网盘转存、搜索渠道与播放参数</p>
      </div>

      <div class="flex items-center gap-2.5">
        <Button size="sm" class="apple-btn-primary px-4 font-medium" :disabled="saving" @click="saveAll">
          {{ saving ? '保存中…' : '保存设置' }}
        </Button>
      </div>
    </header>

    <!-- 紧凑药丸分类导航 -->
    <Tabs v-model="currentNav" :items="navItems" />

    <AccountsSection v-show="currentNav === 'accounts'" />
    <DramaSection v-show="currentNav === 'drama'" ref="dramaRef" @navigate="currentNav = $event" />
    <ChartsSection v-show="currentNav === 'charts'" ref="chartsRef" />
    <SourcesSection
      v-show="currentNav === 'sources'"
      ref="sourcesRef"
      :saving="saving"
      :active="currentNav === 'sources'"
      @save="saveAll"
    />
    <PlaybackSection v-show="currentNav === 'playback'" ref="playbackRef" />
    <SystemSection v-show="currentNav === 'system'" ref="systemRef" />
  </div>
</template>
