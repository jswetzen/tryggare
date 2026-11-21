<script lang="ts">
  import { t } from 'svelte-i18n';
  import { PageHeader, Alert } from '$lib/components/ui';

  let { data } = $props();
  const unavailable = $derived(data.unavailable);
</script>

<div class="max-w-2xl mx-auto">
  <PageHeader title={$t('assistant.unavailable.title')} />
  {#if unavailable}
    <div data-testid="assistant-unavailable">
      <Alert type="warning">
        <p>{$t(`assistant.unavailable.${unavailable.kind}`)}</p>
        {#if unavailable.blockers.length > 0}
          <ul class="mt-2 list-disc pl-5" data-testid="assistant-blockers">
            {#each unavailable.blockers as blocker}
              <li>
                {$t(`assistant.unavailable.blocker.${blocker.code}`, {
                  default: blocker.message
                })}
              </li>
            {/each}
          </ul>
        {/if}
      </Alert>
    </div>
  {/if}
</div>
