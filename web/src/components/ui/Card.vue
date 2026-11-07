<script setup lang="ts">
import { cn } from '@/lib/utils'
</script>
<template>
  <section :class="cn('surface-card overflow-hidden', $attrs.class as string)">
    <slot />
  </section>
</template>
