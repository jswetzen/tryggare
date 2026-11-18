<script lang="ts">
  /**
   * AwaitingConfirmation
   *
   * The collapsed FAMILY row's note that someone in it is a registration the server will refuse
   * until a coordinator confirms it. Same warning tone as the "Awaiting payment" badge, so a
   * coordinator reads it as "not finished" rather than as quiet metadata next to the count line
   * (a neutral grey one was missed on a family that was otherwise checked in). It is a plain
   * <span>, nothing to press. It is NOT used per person: there the plain-text reason line
   * carries the state, because a pill beside a person read as a button to volunteers.
   *
   * Two placements. `inline` is the small pill beside the count line, for a family where only
   * SOME people are blocked. `status` is for a family where EVERYONE is blocked: every other row
   * shows its state on the right ("Check in (1)", "Awaiting payment", "Already checked in"), so
   * this one goes there too, sized like the unpaid badge. The caller passes the padding/type size
   * in `class` for `status` so it can match the layout it sits in.
   *
   * The user-check glyph (Lucide, stroke-only) is what tells this apart from "Awaiting payment"
   * at a glance: same orange family, different cause.
   */
  interface Props {
    label: string;
    testId?: string;
    variant?: 'inline' | 'status';
    class?: string;
  }

  let { label, testId = undefined, variant = 'inline', class: className = '' }: Props = $props();

  // border-warning-200: the config has no 300 step, and a missing one silently renders grey.
  const base = $derived(
    variant === 'status'
      ? 'inline-flex items-center gap-1.5 bg-warning-100 text-warning-800 border border-warning-200 rounded-button whitespace-nowrap'
      : 'inline-flex items-center gap-1 px-2.5 py-0.5 bg-warning-100 text-warning-800 text-xs font-semibold border border-warning-200 rounded-pill whitespace-nowrap'
  );
</script>

<span class="{base} {className}" data-testid={testId}>
  <svg
    class="flex-shrink-0"
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    data-testid={testId ? `${testId}-icon` : undefined}
  >
    <path d="m16 11 2 2 4-4" />
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
  </svg>
  <span>{label}</span>
</span>
