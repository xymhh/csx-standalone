<script setup lang="ts">
defineProps<{modelValue:boolean;label?:string}>();defineEmits<{ 'update:modelValue':[value:boolean] }>()
</script>
<template><button type="button" role="switch" :aria-checked="modelValue" :aria-label="label" class="min-h-[44px] min-w-[44px] p-2" @click="$emit('update:modelValue',!modelValue)"><span class="flex h-6 w-11 items-center rounded-full p-1 transition" :class="modelValue?'bg-primary':'bg-surface-2'"><span class="h-4 w-4 rounded-full bg-bg transition" :class="modelValue?'translate-x-5':'translate-x-0'" /></span></button></template>