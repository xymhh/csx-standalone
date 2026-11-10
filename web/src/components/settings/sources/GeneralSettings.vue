<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ListOrdered, Network, SlidersHorizontal } from '@lucide/vue'
import Input from '@/components/ui/Input.vue'
import { useToast } from '@/composables/useToast'
import { searchSourcesApi } from '@/api/sources'

// 通用设置（排序 / Magnet 模板 / 搜索代理）：自包含状态与保存，保存中状态经 saving-change 同步给父级底部保存栏
const emit = defineEmits<{ 'saving-change': [saving: boolean] }>()

const { toast } = useToast()

const searchProxy = ref('')
const searchProxySaving = ref(false)
const proxyUsername = ref('')
const proxyPassword = ref('')
const sourceOrder = ref<string[]>([])
const resourceOrder = ref<string[]>([])
const magnetTemplate = ref('')
const sourceOptions = ref<{ id: string; name: string }[]>([])
const resourceOptions = ref<{ id: string; name: string }[]>([])
const orderPicker = ref<'' | 'source' | 'resource'>('')

watch(searchProxySaving, (value) => emit('saving-change', value))

async function loadSearchProxy() {
  try {
    const result = await searchSourcesApi.getGlobal()
    searchProxy.value = result.search_proxy || ''
    proxyUsername.value = result.search_proxy_username || ''
    proxyPassword.value = result.search_proxy_password || ''
    sourceOrder.value = [...(result.search_source_order || [])]
    resourceOrder.value = [...(result.resource_type_order || [])]
    magnetTemplate.value = result.magnet_metadata_url_template || ''
    sourceOptions.value = result.source_options || []
    resourceOptions.value = result.resource_options || []
  } catch {
    // 忽略
  }
}

function optionName(options: { id: string; name: string }[], id: string): string {
  return options.find((item) => item.id === id)?.name || id
}

function orderCandidates(kind: 'source' | 'resource') {
  const options = kind === 'source' ? sourceOptions.value : resourceOptions.value
  const chosen = kind === 'source' ? sourceOrder.value : resourceOrder.value
  return options.filter((item) => !chosen.includes(item.id))
}

function addOrderItem(kind: 'source' | 'resource', id: string) {
  if (kind === 'source') sourceOrder.value = [...sourceOrder.value, id]
  else resourceOrder.value = [...resourceOrder.value, id]
  orderPicker.value = ''
}

function removeOrderItem(kind: 'source' | 'resource', id: string) {
  if (kind === 'source') sourceOrder.value = sourceOrder.value.filter((item) => item !== id)
  else resourceOrder.value = resourceOrder.value.filter((item) => item !== id)
}

function moveOrderItem(kind: 'source' | 'resource', id: string, delta: number) {
  const list = kind === 'source' ? [...sourceOrder.value] : [...resourceOrder.value]
  const index = list.indexOf(id)
  const target = index + delta
  if (index < 0 || target < 0 || target >= list.length) return
  list.splice(index, 1)
  list.splice(target, 0, id)
  if (kind === 'source') sourceOrder.value = list
  else resourceOrder.value = list
}

async function saveGlobalSettings() {
  if (magnetTemplate.value && !magnetTemplate.value.includes('{info_hash}')) {
    toast('Magnet 元数据地址模板必须包含 {info_hash}', 'error')
    return
  }
  searchProxySaving.value = true
  try {
    const result = await searchSourcesApi.saveGlobal({
      search_proxy: searchProxy.value.trim(),
      search_proxy_username: proxyUsername.value.trim(),
      search_proxy_password: proxyPassword.value,
      search_source_order: sourceOrder.value,
      resource_type_order: resourceOrder.value,
      magnet_metadata_url_template: magnetTemplate.value.trim(),
    })
    searchProxy.value = result.search_proxy || ''
    proxyUsername.value = result.search_proxy_username || ''
    proxyPassword.value = result.search_proxy_password || ''
    sourceOrder.value = [...(result.search_source_order || [])]
    resourceOrder.value = [...(result.resource_type_order || [])]
    magnetTemplate.value = result.magnet_metadata_url_template || ''
    toast('通用设置已保存', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存通用设置失败', 'error')
  } finally {
    searchProxySaving.value = false
  }
}

async function saveSearchProxy() {
  searchProxySaving.value = true
  try {
    const result = await searchSourcesApi.saveGlobal({ search_proxy: searchProxy.value.trim() })
    searchProxy.value = result.search_proxy
    toast(result.search_proxy ? '搜索代理已保存' : '搜索代理已清空', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '保存搜索代理失败', 'error')
  } finally {
    searchProxySaving.value = false
  }
}

defineExpose({ saveGlobalSettings })

onMounted(() => {
  void loadSearchProxy()
})
</script>

<template>
      <!-- 通用设置：搜索顺序 / Magnet 模板 / 搜索代理 -->
      <div class="apple-glass overflow-hidden rounded-2xl">
        <div class="flex items-center gap-2 px-4 py-3">
          <SlidersHorizontal class="h-4 w-4 shrink-0 text-emerald-400" />
          <h4 class="text-sm font-semibold text-fg">通用设置</h4>
        </div>

        <section class="border-t border-primary/[0.06]">
          <div class="flex items-center gap-2 px-4 py-2.5">
            <ListOrdered class="h-3.5 w-3.5 shrink-0 text-subtle" />
            <span class="text-xs font-semibold text-fg-2">搜索顺序</span>
          </div>

          <div class="border-t border-primary/[0.04] px-4 py-3 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-fg">搜索资源优先级</p>
                <p class="mt-0.5 text-[11px] text-subtle">按顺序依次尝试，靠前的渠道先返回结果</p>
              </div>
              <span class="shrink-0 text-[11px] text-subtle">共 {{ sourceOptions.length }} 项</span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-for="(id, index) in sourceOrder"
                :key="id"
                class="flex items-center gap-1 rounded-lg bg-primary/[0.06] px-2 py-1"
              >
                <span class="text-[10px] font-semibold text-emerald-400">#{{ index + 1 }}</span>
                <span class="text-[11px] text-fg">{{ optionName(sourceOptions, id) }}</span>
                <button type="button" class="px-0.5 text-subtle hover:text-fg disabled:opacity-30 cursor-pointer" :disabled="index === 0" @click="moveOrderItem('source', id, -1)">‹</button>
                <button type="button" class="px-0.5 text-subtle hover:text-fg disabled:opacity-30 cursor-pointer" :disabled="index === sourceOrder.length - 1" @click="moveOrderItem('source', id, 1)">›</button>
                <button type="button" class="px-0.5 text-subtle hover:text-rose-400 cursor-pointer" @click="removeOrderItem('source', id)">✕</button>
              </span>
              <p v-if="!sourceOrder.length" class="text-[11px] text-subtle">未设置优先级，按渠道注册顺序搜索</p>
              <div class="relative">
                <button
                  type="button"
                  class="rounded-lg border border-dashed border-primary/15 px-2 py-1 text-[11px] text-muted hover:border-primary/30 hover:text-fg cursor-pointer"
                  @click="orderPicker = orderPicker === 'source' ? '' : 'source'"
                >+ 添加</button>
                <div
                  v-if="orderPicker === 'source'"
                  class="absolute left-0 top-full z-30 mt-1 max-h-56 w-44 overflow-y-auto rounded-xl border border-primary/10 bg-[#121214] p-1 shadow-2xl"
                >
                  <button
                    v-for="opt in orderCandidates('source')"
                    :key="opt.id"
                    type="button"
                    class="flex w-full items-center rounded-lg px-2 py-1.5 text-left text-[11px] text-fg-2 hover:bg-primary/[0.06] cursor-pointer"
                    @click="addOrderItem('source', opt.id)"
                  >{{ opt.name }}</button>
                  <p v-if="!orderCandidates('source').length" class="px-2 py-1.5 text-[11px] text-subtle">已全部加入</p>
                </div>
              </div>
            </div>
          </div>

          <div class="border-t border-primary/[0.04] px-4 py-3 text-xs">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-fg">资源类型优先级</p>
                <p class="mt-0.5 text-[11px] text-subtle">同一资源命中多个网盘时，按此顺序选择转存目标</p>
              </div>
              <span class="shrink-0 text-[11px] text-subtle">共 {{ resourceOptions.length }} 项</span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-for="(id, index) in resourceOrder"
                :key="id"
                class="flex items-center gap-1 rounded-lg bg-primary/[0.06] px-2 py-1"
              >
                <span class="text-[10px] font-semibold text-emerald-400">#{{ index + 1 }}</span>
                <span class="text-[11px] text-fg">{{ optionName(resourceOptions, id) }}</span>
                <button type="button" class="px-0.5 text-subtle hover:text-fg disabled:opacity-30 cursor-pointer" :disabled="index === 0" @click="moveOrderItem('resource', id, -1)">‹</button>
                <button type="button" class="px-0.5 text-subtle hover:text-fg disabled:opacity-30 cursor-pointer" :disabled="index === resourceOrder.length - 1" @click="moveOrderItem('resource', id, 1)">›</button>
                <button type="button" class="px-0.5 text-subtle hover:text-rose-400 cursor-pointer" @click="removeOrderItem('resource', id)">✕</button>
              </span>
              <div class="relative">
                <button
                  type="button"
                  class="rounded-lg border border-dashed border-primary/15 px-2 py-1 text-[11px] text-muted hover:border-primary/30 hover:text-fg cursor-pointer"
                  @click="orderPicker = orderPicker === 'resource' ? '' : 'resource'"
                >+ 添加</button>
                <div
                  v-if="orderPicker === 'resource'"
                  class="absolute left-0 top-full z-30 mt-1 max-h-56 w-44 overflow-y-auto rounded-xl border border-primary/10 bg-[#121214] p-1 shadow-2xl"
                >
                  <button
                    v-for="opt in orderCandidates('resource')"
                    :key="opt.id"
                    type="button"
                    class="flex w-full items-center rounded-lg px-2 py-1.5 text-left text-[11px] text-fg-2 hover:bg-primary/[0.06] cursor-pointer"
                    @click="addOrderItem('resource', opt.id)"
                  >{{ opt.name }}</button>
                  <p v-if="!orderCandidates('resource').length" class="px-2 py-1.5 text-[11px] text-subtle">已全部加入</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="flex items-start gap-4 border-t border-primary/[0.06] px-4 py-3 text-xs">
          <div class="w-[36%] min-w-[104px] shrink-0">
            <p class="leading-5 font-medium text-fg">Magnet 元数据地址模板</p>
            <p class="mt-0.5 text-[11px] leading-relaxed text-subtle">必须包含 {info_hash}</p>
          </div>
          <div class="min-w-0 flex-1">
            <Input
              v-model="magnetTemplate"
              class="h-9 text-xs"
              placeholder="https://itorrents.org/torrent/{info_hash}.torrent"
            />
          </div>
        </section>

        <section class="border-t border-primary/[0.06]">
          <div class="flex items-center gap-2 px-4 py-2.5">
            <Network class="h-3.5 w-3.5 shrink-0 text-subtle" />
            <span class="text-xs font-semibold text-fg-2">搜索代理</span>
          </div>
          <div class="flex items-start gap-4 border-t border-primary/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-fg">代理地址</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-subtle">留空直连，支持 http / socks5</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="searchProxy" class="h-9 text-xs" placeholder="http://127.0.0.1:7890 或 socks5h://host:1080" />
            </div>
          </div>
          <div class="flex items-start gap-4 border-t border-primary/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-fg">代理用户名</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-subtle">代理需要认证时填写</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="proxyUsername" class="h-9 text-xs" placeholder="留空表示无需认证" />
            </div>
          </div>
          <div class="flex items-start gap-4 border-t border-primary/[0.04] px-4 py-3 text-xs">
            <div class="w-[36%] min-w-[104px] shrink-0">
              <p class="leading-5 font-medium text-fg">代理密码</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-subtle">仅保存在本机数据库</p>
            </div>
            <div class="min-w-0 flex-1">
              <Input v-model="proxyPassword" type="password" class="h-9 text-xs" placeholder="留空表示无需认证" />
            </div>
          </div>
        </section>
      </div>
</template>
