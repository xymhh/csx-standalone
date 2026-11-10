<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import DirectorySelectDialog from '@/components/dialogs/DirectorySelectDialog.vue'
import CategoryCard from '@/components/settings/playback/CategoryCard.vue'
import CrossTransferCard from '@/components/settings/playback/CrossTransferCard.vue'
import EmbyCard from '@/components/settings/playback/EmbyCard.vue'
import OrganizeCard from '@/components/settings/playback/OrganizeCard.vue'
import StrmCard from '@/components/settings/playback/StrmCard.vue'
import { accountsApi } from '@/api/drives'
import { settingsApi } from '@/api/settings'

// 播放与整理：父级持有 strm/organize 表单与目录弹窗，保存时经 collect* 收集各卡片数据（语义与拆分前一致）
const form = ref<Record<string, any>>({
  strm_generate_enabled: true,
  strm_mode: 'direct_302',
  strm_root: '/strm',
  strm_public_base_url: '',
  local_mount_root: '/mnt/quark',
  strm_increment_enabled: false,
  emby_url: '',
  emby_api_key: '',
  emby_refresh_enabled: true,
  organize_source_path: '/CSX/_inbox',
  organize_include_subtitles: true,
  organize_conflict_policy: 'largest',
})

// 网盘账号（全局共享查询，给整理卡片的「浏览」按钮与目录弹窗用）
const accountsQuery = useQuery({
  queryKey: ['accounts'],
  queryFn: () => accountsApi.list(),
})
const accounts = computed(() => accountsQuery.data.value ?? [])

// 目录树选择
const dirDialogOpen = ref(false)
const dirTarget = ref('organize_source_path')

const categoryCardRef = ref<InstanceType<typeof CategoryCard> | null>(null)
const loadedCategory = ref<{ enabled?: boolean; movie?: unknown[]; tv?: unknown[] } | null>(null)

async function loadSettings() {
  try {
    const [t, s, c] = await Promise.all([
      settingsApi.getSection('transfer'),
      settingsApi.getSection('strm'),
      settingsApi.getSection('category'),
    ])
    Object.assign(form.value, t, s)
    const strmSection = s as { mode?: string; public_base_url?: string }
    if (strmSection.mode) form.value.strm_mode = strmSection.mode
    if (strmSection.public_base_url) {
      form.value.strm_public_base_url = String(strmSection.public_base_url)
    }
    loadedCategory.value = c as { enabled?: boolean }
    categoryCardRef.value?.applyCategory(c as { enabled?: boolean })
  } catch (cause) {
    console.error(cause)
  }
}

function openDirBrowse(target: string) {
  dirTarget.value = target
  dirDialogOpen.value = true
}

function handleDirSelect(path: string) {
  if (dirTarget.value === 'organize_source_path') {
    form.value.organize_source_path = path
  } else if (dirTarget.value === 'local_mount_root') {
    form.value.local_mount_root = path
  }
  dirDialogOpen.value = false
}

function collectTransfer() {
  return {
    organize_source_path: form.value.organize_source_path,
    organize_include_subtitles: form.value.organize_include_subtitles,
    organize_conflict_policy: form.value.organize_conflict_policy,
  }
}

function collectStrm() {
  return {
    strm_generate_enabled: form.value.strm_generate_enabled,
    mode: form.value.strm_mode,
    strm_root: form.value.strm_root,
    public_base_url: form.value.strm_public_base_url,
    local_mount_root: form.value.local_mount_root,
    strm_increment_enabled: form.value.strm_increment_enabled,
    emby_url: form.value.emby_url,
    emby_api_key: form.value.emby_api_key,
    emby_refresh_enabled: form.value.emby_refresh_enabled,
  }
}

function collectCategory() {
  // 子组件已挂载时以其状态为准；极端情况下回退到最近一次加载的 section 数据
  return (
    categoryCardRef.value?.collectCategory() ?? {
      enabled: loadedCategory.value?.enabled ?? true,
      movie: loadedCategory.value?.movie ?? [],
      tv: loadedCategory.value?.tv ?? [],
    }
  )
}

defineExpose({ collectTransfer, collectStrm, collectCategory })

onMounted(() => {
  void loadSettings()
})
</script>

<template>
  <!-- 5. 播放与整理 (紧凑卡片网格) -->
  <div class="space-y-5">
    <div class="grid gap-4 md:grid-cols-2">
      <StrmCard v-model:form="form" />
      <EmbyCard v-model:form="form" />
    </div>

    <OrganizeCard v-model:form="form" :accounts="accounts" @browse="openDirBrowse" />
    <CrossTransferCard />
    <CategoryCard ref="categoryCardRef" />

    <!-- 目录树选择弹窗：Dialog 内部 Teleport 到 body，放在根节点内不影响布局；
           必须留在唯一根节点内，否则 v-show 无法作用于组件（多根节点会被忽略） -->
    <DirectorySelectDialog
      v-if="dirDialogOpen"
      :open="dirDialogOpen"
      :accounts="accounts"
      :account-id="accounts[0]?.id"
      @close="dirDialogOpen = false"
      @select="handleDirSelect"
    />
  </div>
</template>
