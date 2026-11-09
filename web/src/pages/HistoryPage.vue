<script setup lang="ts">
import TransferHistory from '@/components/domain/TransferHistory.vue'
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-xl font-semibold tracking-tight text-fg">转存历史</h2>
      <p class="mt-0.5 text-xs text-muted">
        按影视汇总的转存流水，点开可看到每一集的文件名、大小、来源与失败原因
      </p>
    </div>
    <TransferHistory />
  </div>
</template>
