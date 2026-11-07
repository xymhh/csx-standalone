<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, RefreshCw, Trash2, Pause, Play, Film } from '@lucide/vue'

import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Input from '@/components/ui/Input.vue'
import { useToast } from '@/composables/useToast'
import { subscriptionsApi, type Subscription } from '@/lib/api'

const rows = ref<Subscription[]>([])
const open = ref(false)
const tmdb = ref('')
const { toast } = useToast()

async function load() {
  rows.value = await subscriptionsApi.list()
}

onMounted(load)

async function create() {
  try {
    await subscriptionsApi.create({ tmdb_id: Number(tmdb.value) })
    open.value = false
    tmdb.value = ''
    await load()
    toast('已添加追剧订阅', 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '添加失败', 'error')
  }
}

async function toggle(row: Subscription) {
  await subscriptionsApi.update(row.id, {
    state: row.state === 'active' ? 'paused' : 'active',
  })
  await load()
  toast(row.state === 'active' ? '已暂停追剧' : '已恢复追剧', 'info')
}

async function sync(id: number) {
  try {
    const response = await subscriptionsApi.sync(id)
    toast(response.message, 'success')
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '同步找源失败', 'error')
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-2xl font-semibold tracking-tight text-fg">我的追剧清单</h2>
        <p class="mt-1 text-sm text-muted">管理你正在追的电视剧和电影，系统会自动全网找源并转存最新更新</p>
      </div>
      <Button @click="open = true" class="flex items-center gap-2">
        <Plus class="h-4 w-4" />
        <span>添加追剧</span>
      </Button>
    </div>

    <div v-if="!rows.length" class="rounded-2xl border border-dashed border-border bg-surface/40 p-12 text-center text-sm text-muted">
      <Film class="mx-auto mb-3 h-8 w-8 text-muted" />
      <p class="font-medium text-fg">你的追剧清单还是空的</p>
      <p class="mt-1 text-xs text-muted">点击右上角「添加追剧」，输入影视编号或名称即可开始全自动追更。</p>
    </div>

    <div class="grid gap-3.5 md:grid-cols-2 xl:grid-cols-3">
      <article v-for="row in rows" :key="row.id" class="rounded-xl border border-border bg-surface p-5 transition-all hover:border-zinc-700">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold text-fg">{{ row.media?.title ?? `影视 #${row.media_id}` }}</h3>
            <p class="mt-1 text-xs text-muted">来源：{{ row.source }} · 编号 #{{ row.id }}</p>
          </div>
          <Badge :tone="row.state === 'active' ? 'good' : 'muted'" :pulse="row.state === 'active'">
            {{ row.state === 'active' ? '正在追更' : '已暂停' }}
          </Badge>
        </div>

        <div class="mt-4 flex flex-wrap gap-2 pt-2 border-t border-border/60">
          <Button variant="outline" size="sm" @click="toggle(row)">
            <component :is="row.state === 'active' ? Pause : Play" class="mr-1.5 h-3.5 w-3.5" />
            {{ row.state === 'active' ? '暂停' : '继续追' }}
          </Button>
          <Button variant="outline" size="sm" @click="sync(row.id)">
            <RefreshCw class="mr-1.5 h-3.5 w-3.5" />
            立即找资源
          </Button>
          <Button variant="ghost" size="sm" class="text-rose-400 hover:text-rose-300 ml-auto" @click="subscriptionsApi.delete(row.id).then(load)">
            <Trash2 class="h-3.5 w-3.5" />
          </Button>
        </div>
      </article>
    </div>

    <Dialog :open="open" title="添加追剧" @close="open = false">
      <form class="space-y-4" @submit.prevent="create">
        <label class="block space-y-1.5 text-sm">
          <span class="font-medium text-fg">TMDB 影视编号</span>
          <Input v-model="tmdb" type="number" min="1" required placeholder="例如：12345" />
          <span class="text-xs text-muted">输入电视剧或电影在 TMDB 的 ID 编号，系统将自动拉取剧集元数据</span>
        </label>
        <Button type="submit" class="w-full">立即添加并开始监控</Button>
      </form>
    </Dialog>
  </div>
</template>
