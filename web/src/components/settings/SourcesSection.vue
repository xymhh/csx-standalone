<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from '@/components/ui/Button.vue'
import GeneralSettings from '@/components/settings/sources/GeneralSettings.vue'
import SourceDetail from '@/components/settings/sources/SourceDetail.vue'
import SourceTabs from '@/components/settings/sources/SourceTabs.vue'
import { useToast } from '@/composables/useToast'
import { type SearchSourceSchema, searchSourcesApi } from '@/api/sources'

// 搜索渠道设置：父级持有渠道 schema 与全部字段值（保存给后端的是整份 sourceValues），
// 切换栏 / 通用设置 / 单渠道详情拆为子组件，保存编排仍在本组件（语义与拆分前一致）
const props = defineProps<{ saving: boolean; active: boolean }>()
const emit = defineEmits<{ save: [] }>()

const { toast } = useToast()

const sourceSchemas = ref<SearchSourceSchema[]>([])
const sourceValues = ref<Record<string, Record<string, any>>>({})
const selectedSourceId = ref('general')

const generalRef = ref<InstanceType<typeof GeneralSettings> | null>(null)
const detailRef = ref<InstanceType<typeof SourceDetail> | null>(null)
const generalSaving = ref(false)

const currentSource = computed(() => sourceSchemas.value.find((s) => s.id === selectedSourceId.value))

async function loadSources() {
  try {
    const schemas = await searchSourcesApi.schema()
    sourceSchemas.value = schemas
    const values: Record<string, Record<string, any>> = {}
    for (const schema of schemas) {
      const current: Record<string, any> = { enabled: schema.enabled ?? true }
      for (const group of schema.groups) {
        for (const field of group.fields) {
          current[field.key] = field.value ?? field.default ?? ''
        }
      }
      values[schema.id] = current
    }
    sourceValues.value = values
    if (!selectedSourceId.value || !schemas.some((s) => s.id === selectedSourceId.value)) {
      selectedSourceId.value = 'general'
    }
  } catch {
    // 渠道 schema 拉取失败时保持空列表，页面其余部分照常渲染
  }
}

// 底部保存按钮：通用设置页签走 GeneralSettings 自己的保存，其余渠道走父级 saveAll 的 sources 分支
function onBottomSave() {
  if (selectedSourceId.value === 'general') {
    void generalRef.value?.saveGlobalSettings()
  } else {
    emit('save')
  }
}

// 父级「保存设置」在搜索渠道页签下的保存动作（与原 saveAll 的 sources 分支一致）
async function saveSources() {
  await searchSourcesApi.save(sourceValues.value)
  toast('15 个搜索渠道设置已保存', 'success')
  void detailRef.value?.reloadMeta()
}

defineExpose({ saveSources })

onMounted(() => {
  void loadSources()
})
</script>

<template>
    <!-- 4. 搜索渠道（对齐原版插件：药丸标签 + 账户卡片 + 行式字段 + 底部保存） -->
    <div class="space-y-4 pb-28">
      <SourceTabs v-model:selected="selectedSourceId" :schemas="sourceSchemas" :values="sourceValues" />

      <GeneralSettings
        v-if="selectedSourceId === 'general'"
        ref="generalRef"
        @saving-change="generalSaving = $event"
      />

      <SourceDetail
        v-else-if="currentSource"
        ref="detailRef"
        v-model:source-values="sourceValues"
        :source="currentSource"
        :selected="selectedSourceId"
        :active="props.active"
      />

      <!-- 底部保存 -->
      <div class="sticky bottom-0 z-20 pt-1">
        <div class="apple-glass flex items-center justify-between gap-3 rounded-2xl px-3 py-2.5 shadow-xl">
          <p class="text-[11px] text-subtle">
            <template v-if="selectedSourceId === 'general'">通用设置 · 排序 / Magnet / 代理</template>
            <template v-else>共 {{ sourceSchemas.length }} 个渠道 · 当前 {{ currentSource?.name || '—' }}</template>
          </p>
          <Button
            size="sm"
            class="apple-btn-primary px-4 text-xs"
            :disabled="saving || generalSaving"
            @click="onBottomSave"
          >
            {{ saving || generalSaving ? '保存中…' : '保存配置' }}
          </Button>
        </div>
      </div>
    </div>
</template>
