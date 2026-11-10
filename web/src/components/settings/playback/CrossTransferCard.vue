<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Link2 } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Switch from '@/components/ui/Switch.vue'
import { useToast } from '@/composables/useToast'
import { type CrossTransferSettings, crossTransferApi } from '@/api/settings'

// 跨盘转存：配置自包含（独立接口、独立保存按钮，不走父级 saveAll）
const { toast } = useToast()

const crossSaving = ref(false)
const crossCfg = ref<CrossTransferSettings>({
  enabled: true,
  library_drive: '',
  download_threads: 5,
  max_concurrent: 2,
  direct_stream: true,
  cache_dir: '/cache',
  cache_free_gb: 0,
  drive_options: [],
})

async function loadCrossSettings() {
  try {
    crossCfg.value = await crossTransferApi.get()
  } catch (cause) {
    console.error(cause)
  }
}

async function saveCrossSettings() {
  crossSaving.value = true
  try {
    crossCfg.value = await crossTransferApi.save({
      enabled: crossCfg.value.enabled,
      library_drive: crossCfg.value.library_drive,
      download_threads: Number(crossCfg.value.download_threads),
      max_concurrent: Number(crossCfg.value.max_concurrent),
      direct_stream: crossCfg.value.direct_stream,
    })
    toast('跨盘转存设置已保存', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存失败', 'error')
  } finally {
    crossSaving.value = false
  }
}

onMounted(() => {
  void loadCrossSettings()
})
</script>

<template>
      <!-- 卡片 C2: 跨盘转存 -->
      <div class="apple-glass rounded-2xl p-5 space-y-3 text-xs">
        <div class="flex items-center justify-between border-b border-primary/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <Link2 class="h-4 w-4 text-sky-400" />
            <h3 class="text-sm font-semibold text-fg">跨盘转存</h3>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-[11px] text-subtle">缓存剩余 {{ crossCfg.cache_free_gb }} GB</span>
            <Switch v-model="crossCfg.enabled" />
          </div>
        </div>
        <p class="text-[11px] leading-relaxed text-subtle">
          资源盘和媒体库盘不是同一个网盘时（例如夸克分享、115 媒体库），先下载到本地缓存，再秒传或上传到媒体库盘；同盘仍然直接转存。
        </p>
        <div v-if="!crossCfg.drive_options.length" class="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[11px] text-amber-300">
          还没有可用的媒体库网盘，先到「网盘账号」绑定 115 或夸克。
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label class="font-medium text-fg">媒体库所在网盘</label>
            <Select
              v-model="crossCfg.library_drive"
              :options="crossCfg.drive_options.map((item) => ({ value: item.value, label: item.primary ? item.label + '（主号）' : item.label }))"
            />
          </div>
          <div class="space-y-1.5">
            <label class="font-medium text-fg">下载线程数</label>
            <Input v-model.number="crossCfg.download_threads" type="number" min="1" max="16" />
          </div>
          <div class="space-y-1.5">
            <label class="font-medium text-fg">同时中继任务数</label>
            <Input v-model.number="crossCfg.max_concurrent" type="number" min="1" max="4" />
          </div>
          <div class="flex items-center justify-between rounded-xl bg-surface-solid/50 p-3 border border-primary/[0.06]">
            <div>
              <p class="font-medium text-fg">边下边传</p>
              <p class="text-[11px] text-subtle">下载一块上传一块，省等待</p>
            </div>
            <Switch v-model="crossCfg.direct_stream" />
          </div>
        </div>
        <div class="flex items-center justify-between pt-1">
          <p class="text-[11px] text-subtle">缓存目录 {{ crossCfg.cache_dir }}</p>
          <Button size="sm" :disabled="crossSaving" @click="saveCrossSettings">
            {{ crossSaving ? '保存中…' : '保存跨盘设置' }}
          </Button>
        </div>
      </div>
</template>
