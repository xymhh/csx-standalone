<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CandidateCard from '@/components/domain/CandidateCard.vue'
import { useToast } from '@/composables/useToast'
import { candidatesApi, type Candidate } from '@/lib/api'

const rows = ref<Candidate[]>([])
const { toast } = useToast()

async function load() {
  rows.value = await candidatesApi.list({ state: 'discovered' })
}

onMounted(load)

async function accept(id: number) {
  try {
    const response = await candidatesApi.accept(id)
    toast(`已提交转存任务 #${response.task_id}，正在开始下载`, 'success')
    await load()
  } catch (cause) {
    toast(cause instanceof Error ? cause.message : '转存失败', 'error')
  }
}

async function ignore(id: number) {
  await candidatesApi.ignore(id)
  toast('已忽略该资源', 'info')
  await load()
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-fg">待选资源</h2>
      <p class="mt-1 text-sm text-muted">系统在全网搜集到的影视分享链接，你可以手动一键存入自己的网盘，或由系统自动择优转存</p>
    </div>

    <div v-if="!rows.length" class="rounded-2xl border border-dashed border-border bg-surface/40 p-12 text-center text-sm text-muted">
      目前没有等待处理的分享资源。系统正在后台自动寻找新资源。
    </div>

    <div class="grid gap-3.5 lg:grid-cols-2">
      <CandidateCard
        v-for="candidate in rows"
        :key="candidate.id"
        :candidate="candidate"
        @accept="accept"
        @ignore="ignore"
      />
    </div>
  </div>
</template>
