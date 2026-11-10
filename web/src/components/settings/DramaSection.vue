<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AdvancedCard from '@/components/settings/drama/AdvancedCard.vue'
import AutoSearchCard from '@/components/settings/drama/AutoSearchCard.vue'
import NamingCard from '@/components/settings/drama/NamingCard.vue'
import StorageCard from '@/components/settings/drama/StorageCard.vue'
import TrackingCard from '@/components/settings/drama/TrackingCard.vue'
import TransferCard from '@/components/settings/drama/TransferCard.vue'
import { settingsApi } from '@/api/settings'

const emit = defineEmits<{ navigate: [value: string] }>()

// baseline + transfer 两份 section 合并进同一份 form，由各卡片以 v-model:form 共享编辑
const form = ref<Record<string, any>>({
  enabled: true,
  title_subscribe_enabled: true,
  subscribe_all_missing_seasons: false,
  subscribe_skip_season_zero: true,
  subscribe_season_limit: 0,
  window_days: 14,
  language: 'zh-CN',
  tmdb_api_key: '',
  default_drive: 'quark',
  type_folder_enabled: false,
  type_folder_movie: '电影',
  type_folder_tv: '电视剧',
  enable_cloud_upgrade: true,
  enable_pt_upgrade: false,
  min_quality: 'hd',
  min_episode_size_mb: 100,
  cross_transfer_enabled: true,
  cross_transfer_threads: 3,
  cross_transfer_direct_stream: false,
})

const namingCardRef = ref<InstanceType<typeof NamingCard> | null>(null)

async function loadSettings() {
  try {
    const [b, t] = await Promise.all([
      settingsApi.getSection('baseline'),
      settingsApi.getSection('transfer'),
    ])
    Object.assign(form.value, b, t)
  } catch (cause) {
    console.error(cause)
  }
}

function collectBaseline() {
  return {
    enabled: form.value.enabled,
    title_subscribe_enabled: form.value.title_subscribe_enabled,
    subscribe_all_missing_seasons: form.value.subscribe_all_missing_seasons,
    subscribe_skip_season_zero: form.value.subscribe_skip_season_zero,
    subscribe_season_limit: Number(form.value.subscribe_season_limit),
    window_days: Number(form.value.window_days),
    language: form.value.language,
    tmdb_api_key: form.value.tmdb_api_key,
  }
}

function collectTransfer() {
  return {
    default_drive: form.value.default_drive,
    type_folder_enabled: form.value.type_folder_enabled,
    type_folder_movie: form.value.type_folder_movie,
    type_folder_tv: form.value.type_folder_tv,
    enable_cloud_upgrade: form.value.enable_cloud_upgrade,
    enable_pt_upgrade: form.value.enable_pt_upgrade,
    min_quality: form.value.min_quality,
    min_episode_size_mb: Number(form.value.min_episode_size_mb),
  }
}

// 保存重命名模板：转发给 NamingCard（失败不抛错、返回错误信息的软失败语义不变）
async function saveNaming(): Promise<string> {
  return namingCardRef.value?.saveNaming() ?? ''
}

defineExpose({ collectBaseline, collectTransfer, saveNaming })

onMounted(() => {
  void loadSettings()
})
</script>

<template>
    <!-- 2. 追剧与规则 (紧凑卡片网格 Bento Grid) -->
    <div class="space-y-5">
      <div class="grid gap-4 md:grid-cols-2">
        <TrackingCard v-model:form="form" />
        <AutoSearchCard />
        <TransferCard v-model:form="form" />
      </div>

      <StorageCard v-model:form="form" @navigate="emit('navigate', $event)" />
      <NamingCard ref="namingCardRef" />
      <AdvancedCard v-model:form="form" />
    </div>
</template>
