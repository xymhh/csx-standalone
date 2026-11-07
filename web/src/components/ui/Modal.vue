<script setup lang="ts">
import Dialog from './Dialog.vue'
defineProps<{ open: boolean; title: string }>()
defineEmits<{ close: [] }>()
</script>
<template><Dialog :open="open" :title="title" @close="$emit('close')"><slot /></Dialog></template>
