<script lang="ts">
  interface Props {
    title: string;
    count?: number;
  }

  let { title, count }: Props = $props();
</script>

<div class="flex justify-between items-center my-5 pb-2 border-b border-neutral-200">
  <h2 class="text-lg font-semibold text-neutral-700">{title}</h2>
  {#if count !== undefined}
    <span class="text-sm text-neutral-500">{count} families</span>
  {/if}
</div>
