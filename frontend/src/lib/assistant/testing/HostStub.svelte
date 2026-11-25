<script lang="ts">
  // Stand-in for AssistantHost in page tests: shows what the page passed.
  let {
    eventId,
    previewSource,
    previewStale,
    previewDraftUnusable,
    reload
  }: {
    eventId: string;
    previewSource: string;
    previewStale: boolean;
    previewDraftUnusable: boolean;
    reload: () => unknown;
    store?: unknown;
  } = $props();
</script>

<div
  data-testid="host-stub"
  data-event={eventId}
  data-source={previewSource}
  data-stale={previewStale}
  data-unusable={previewDraftUnusable}
>
  <button type="button" onclick={() => reload()}>stub reload</button>
</div>
