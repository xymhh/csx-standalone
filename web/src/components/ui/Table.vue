<template>
  <div class="w-full overflow-x-auto rounded-xl border border-border bg-surface shadow-sm shadow-black/40">
    <table
      class="w-full border-collapse text-left text-sm [&_thead]:bg-surface-2/40 [&_thead]:text-xs [&_thead]:uppercase [&_thead]:tracking-wider [&_thead]:text-muted [&_th]:font-medium [&_th]:whitespace-nowrap [&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-surface-2/40 [&_td]:tabular-nums [&_tr:last-child_td]:border-b-0"
    >
      <slot />
    </table>
  </div>
</template>
