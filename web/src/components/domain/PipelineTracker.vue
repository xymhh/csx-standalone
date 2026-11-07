<script setup lang="ts">
const steps=['订阅基准','追更缺集','双源发现','候选决策','转存入库'];defineProps<{active?:number}>()
</script>
<template><ol class="grid grid-cols-2 gap-2 sm:grid-cols-5"><li v-for="(step,i) in steps" :key="step" class="flex min-h-12 items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm"><span class="grid h-7 w-7 place-items-center rounded-full" :class="i<=(active??0)?'bg-primary text-bg':'bg-surface-2 text-muted'">{{i+1}}</span><span>{{step}}</span></li></ol></template>