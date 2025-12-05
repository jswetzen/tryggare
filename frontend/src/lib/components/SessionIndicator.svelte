<script lang="ts">
  import { t } from 'svelte-i18n';

  interface Props {
    eventName: string;
    sessionName: string;
    sessionTime: string;
    onChangeSession?: () => void;
  }

  let { eventName, sessionName, sessionTime, onChangeSession }: Props = $props();
</script>

<div class="bg-neutral-50 border border-neutral-300 rounded-card px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm">
  <div class="text-neutral-600">
    <span class="font-semibold text-primary-900">{$t('session.event')}</span> {eventName} •
    <span class="font-semibold text-primary-900 ml-1">{$t('session.session')}</span> {sessionName} ({sessionTime})
  </div>
  {#if onChangeSession}
    <button
      onclick={onChangeSession}
      class="text-primary-600 font-semibold hover:underline"
    >
      {$t('session.changeSession')}
    </button>
  {/if}
</div>
