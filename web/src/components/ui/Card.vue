<template><section :class="cn('rounded-card border border-border bg-surface', $attrs.class as string)"><slot /></section></template>
<script setup lang="ts">
import { cn } from '@/lib/utils'
</script>