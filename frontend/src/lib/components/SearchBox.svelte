<script lang="ts">
  interface Props {
    value: string;
    placeholder?: string;
    label?: string;
    onInput?: (value: string) => void;
  }

  let {
    value = $bindable(''),
    placeholder = "Search by last name or first name...",
    label = "Search Families",
    onInput
  }: Props = $props();

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = target.value;
    if (onInput) {
      onInput(target.value);
    }
  }
</script>

<div class="border-2 border-blue-500 rounded-md p-3 mb-5 bg-blue-50">
  <label class="block font-semibold text-blue-900 mb-2 text-sm">
    {label}
  </label>
  <input
    type="text"
    {value}
    oninput={handleInput}
    {placeholder}
    class="w-full px-3 py-2 border border-slate-300 rounded bg-white text-sm"
  />
</div>
