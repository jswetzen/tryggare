<script lang="ts">
  interface Props {
    title: string;
  }

  let { title }: Props = $props();
</script>

<h1 class="text-primary-900 text-h1 mb-5 pb-2 border-b-2 border-neutral-200">
  {title}
</h1>
