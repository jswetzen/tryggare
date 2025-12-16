<script lang="ts">
  import SearchBox from '$lib/components/SearchBox.svelte';

  interface Props {
    value: string;
    placeholder?: string;
    label?: string;
    onInput?: (value: string) => void;
    class?: string;
  }

  let {
    value = $bindable(''),
    placeholder,
    label,
    onInput,
    class: className = ''
  }: Props = $props();
</script>

<div class="sticky top-0 z-10 bg-slate-100 pb-2 -mx-3 px-3 md:-mx-5 md:px-5 {className}">
  <SearchBox
    bind:value={value}
    placeholder={placeholder}
    label={label}
    onInput={onInput}
  />
</div>
