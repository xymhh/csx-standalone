<script setup lang="ts">
import { ChevronDown, ChevronRight, Folder, LoaderCircle } from '@lucide/vue'

import type { DriveFolder } from '@/api/drives'

defineProps<{
  folder: DriveFolder
  children: Record<string, DriveFolder[]>
  expanded: Record<string, boolean>
  loading: Record<string, boolean>
  selected: string
}>()
const emit = defineEmits<{ toggle: [folder: DriveFolder]; choose: [folder: DriveFolder] }>()
</script>

<template>
  <div class="space-y-0.5">
    <div class="flex min-h-11 items-center gap-1 rounded-lg px-1 hover:bg-surface-2" :class="selected === folder.path ? 'bg-surface-2' : ''">
      <button class="grid h-9 w-9 shrink-0 place-items-center rounded-md text-muted hover:text-fg" @click="emit('toggle', folder)">
        <LoaderCircle v-if="loading[folder.id]" class="h-4 w-4 animate-spin" />
        <ChevronDown v-else-if="expanded[folder.id]" class="h-4 w-4" />
        <ChevronRight v-else class="h-4 w-4" />
      </button>
      <button class="flex min-h-11 min-w-0 flex-1 items-center gap-2 text-left text-sm text-fg" @click="emit('choose', folder)">
        <Folder class="h-4 w-4 shrink-0 text-primary" />
        <span class="truncate">{{ folder.name }}</span>
      </button>
    </div>
    <div v-if="expanded[folder.id]" class="ml-5 border-l border-border/50 pl-2">
      <DirectoryTreeNode
        v-for="child in children[folder.id] ?? []"
        :key="child.id"
        :folder="child"
        :children="children"
        :expanded="expanded"
        :loading="loading"
        :selected="selected"
        @toggle="emit('toggle', $event)"
        @choose="emit('choose', $event)"
      />
    </div>
  </div>
</template>
