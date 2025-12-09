<script lang="ts">
  interface Props {
    title: string;
    count?: number;
  }

  let { title, count }: Props = $props();
</script>

<div class="flex justify-between items-center my-5 pb-2 border-b border-slate-200">
  <h2 class="text-lg font-semibold text-slate-700">{title}</h2>
  {#if count !== undefined}
    <span class="text-sm text-slate-500">{count} families</span>
  {/if}
</div>
