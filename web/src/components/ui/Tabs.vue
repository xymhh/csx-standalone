<script setup lang="ts">
defineProps<{modelValue:string;items:{value:string;label:string}[]}>();defineEmits<{ 'update:modelValue':[value:string] }>()
</script>
<template><div class="flex gap-1 overflow-x-auto border-b border-border"><button v-for="item in items" :key="item.value" class="min-h-[44px] shrink-0 border-b-2 px-3 text-sm" :class="modelValue===item.value?'border-primary text-fg':'border-transparent text-muted'" @click="$emit('update:modelValue',item.value)">{{item.label}}</button></div></template>