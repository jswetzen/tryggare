<script lang="ts">
  /**
   * The feature request cards of one conversation, in the chat body (outside the
   * transcript log, so a card does not read as a message). The status line is the
   * one live region for them: it announces a new card and a settled one.
   */
  import { t } from 'svelte-i18n';
  import FeatureRequestCard from './FeatureRequestCard.svelte';
  import type { FeatureRequestCard as Card } from './types';

  let {
    eventId,
    cards,
    ondone,
    onremoved
  }: {
    eventId: string;
    cards: Card[];
    ondone: (id: string, outcome: 'confirmed' | 'duplicate', duplicateOf: string | null, title: string) => void;
    onremoved: (id: string) => void;
  } = $props();

  let announce = $state('');
  // A discard leaves no card to diff against, so the card reports it itself.
  const discarded = (id: string) => (announce = $t('assistant.featureRequest.announce.discarded', { values: { id } }));
  // Cards already on screen when this mounted are not announced: they are not news.
  // Each message names the card, so a second new card is not the same text (no re-announce).
  const seen = new Map<string, Card['outcome']>();
  let primed = false;

  $effect(() => {
    for (const card of cards) {
      if (!seen.has(card.id)) {
        if (primed) announce = $t('assistant.featureRequest.announce.new', { values: { id: card.id } });
      } else if (!seen.get(card.id) && card.outcome) {
        announce =
          card.outcome === 'duplicate'
            ? $t('assistant.featureRequest.announce.joined', { values: { id: card.id } })
            : $t('assistant.featureRequest.announce.saved', { values: { id: card.id } });
      }
      seen.set(card.id, card.outcome);
    }
    primed = true;
  });
</script>

{#if cards.length > 0}
  <section class="cards" aria-labelledby="assistant-feature-heading" data-testid="assistant-feature-requests">
    <h3 id="assistant-feature-heading" class="sr-only">{$t('assistant.featureRequest.heading')}</h3>
    {#each cards as card (card.id)}
      <FeatureRequestCard {eventId} {card} {ondone} {onremoved} ondiscarded={discarded} />
    {/each}
  </section>
{/if}
<p class="sr-only" role="status" aria-live="polite" data-testid="assistant-feature-status">{announce}</p>

<style>
  .cards {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
</style>
