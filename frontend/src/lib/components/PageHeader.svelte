<script lang="ts">
  interface Props {
    title: string;
  }

  let { title }: Props = $props();
</script>

<h1 class="text-blue-900 text-2xl font-bold mb-5 pb-2 border-b-2 border-slate-200">
  {title}
</h1>
