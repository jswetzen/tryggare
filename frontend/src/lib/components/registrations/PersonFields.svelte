<script lang="ts" module>
  import type { HealthInfoStatus } from '$lib/components/checkin/ConsentCapture.svelte';

  // The row fields PersonFields reads and writes; ParentRow and ChildRow on
  // the register page both satisfy it.
  export interface PersonRowFields {
    first_name: string;
    last_name: string;
    phone?: string;
    email?: string;
    relationship_type?: string;
    birthdate?: string;
    birthdateRangeInvalid?: boolean;
    allergies: string;
    notes: string;
    healthInfoStatus: HealthInfoStatus;
    consentNoticeShared: boolean;
  }
</script>

<script lang="ts">
  import type { Snippet } from 'svelte';
  import { t, locale } from 'svelte-i18n';
  import ConsentCapture from '$lib/components/checkin/ConsentCapture.svelte';
  import type { RegistrationFormSpec } from '$lib/api/types';
  import { isFieldRequired, isFieldVisible, type FieldGroup } from '$lib/registration/formSpec';

  /**
   * The person input fields of one parent or child card, rendered from
   * spec.fields[group] in spec order. Ticket select and extras stay on the
   * page and arrive through `middle`; the health block (ConsentCapture) is
   * gated by the spec's health_consent_status / allergies / notes flags.
   */
  interface Props {
    spec: RegistrationFormSpec;
    group: FieldGroup;
    index: number;
    row: PersonRowFields;
    problems: { id: string; message: string }[];
    onClearProblem: (id: string) => void;
    // Parent only: guardian-only adults carry no health data and are not asked.
    guardianOnly?: boolean;
    // Parent only: Förälder 1's first name is asked for while there is a child.
    childCount?: number;
    firstNameProblem?: string | null;
    relationshipMissing?: boolean;
    // Child only.
    birthdateProse?: string;
    onBirthdateChange?: (event: Event) => void;
    minBirthdate?: string;
    maxBirthdate?: string;
    middle?: Snippet;
  }

  let {
    spec,
    group,
    index,
    row = $bindable(),
    problems,
    onClearProblem,
    guardianOnly = false,
    childCount = 0,
    firstNameProblem = null,
    relationshipMissing = false,
    birthdateProse = '',
    onBirthdateChange,
    minBirthdate,
    maxBirthdate,
    middle
  }: Props = $props();

  const hasProblem = (id: string) => problems.some((p) => p.id === id);
  const problemMessage = (id: string) => problems.find((p) => p.id === id)?.message ?? null;

  const inputBase = 'w-full px-2 py-1.5 text-sm border rounded-button focus:outline-none focus:ring-2';
  const okBorder = 'border-neutral-300 focus:ring-primary-500';
  const badBorder = 'border-danger-600 focus:ring-danger-500 focus:border-danger-600';

  const required = (key: string) => isFieldRequired(spec, group, key);
  // Förälder 1's first name is only asked for while there is a child to
  // be guardian of; other parent rows are optional as a whole.
  const firstNameRequired = $derived(
    group === 'child'
      ? required('first_name')
      : required('first_name') && index === 0 && childCount > 0
  );

  const keys = $derived(
    spec.fields[group]
      .filter((f) => f.visible)
      .map((f) => f.key)
      .filter((k) =>
        group === 'parent'
          ? ['first_name', 'last_name', 'phone', 'email', 'relationship_type'].includes(k)
          : ['first_name', 'last_name', 'birthdate'].includes(k)
      )
  );

  const showConsent = $derived(
    isFieldVisible(spec, group, 'health_consent_status') && !(group === 'parent' && guardianOnly)
  );
</script>

{#snippet star()}
  <span class="text-danger-600" aria-hidden="true">*</span>
{/snippet}

{#snippet consent()}
  <ConsentCapture
    bind:status={row.healthInfoStatus}
    bind:allergies={row.allergies}
    bind:notes={row.notes}
    bind:consentNoticeShared={row.consentNoticeShared}
    idPrefix={group === 'parent' ? `parent-${index}` : String(index)}
    testIdPrefix={group === 'parent' ? 'parent' : undefined}
    attestLabelKey="register.consentAttest"
    questionKey={group === 'parent' ? 'register.adultHealthInfoQuestion' : undefined}
    consentLabelKey={group === 'parent' ? 'register.adultHealthInfoConsent' : undefined}
    declineLabelKey={group === 'parent' ? 'register.adultHealthInfoDecline' : undefined}
    noticeKey={group === 'parent' ? 'register.adultHealthConsentNotice' : undefined}
    declinedNoteKey={group === 'parent' ? 'register.adultHealthInfoDeclinedNote' : undefined}
    noticeLinkHref={group === 'parent' ? '/privacy' : undefined}
    showAllergies={isFieldVisible(spec, group, 'allergies')}
    showNotes={isFieldVisible(spec, group, 'notes')}
  />
{/snippet}

{#snippet personFields()}
  {#each keys as key (key)}
    {#if group === 'parent'}
      {#if key === 'first_name'}
        <div>
          <label for={`parent-first-name-${index}`} class="block text-xs text-neutral-600 mb-1">
            {$t('checkin.parentFirstName')}
            {#if firstNameRequired}{@render star()}{/if}
          </label>
          <input
            id={`parent-first-name-${index}`}
            type="text"
            bind:value={row.first_name}
            oninput={() => {
              onClearProblem(`parent-first-name-${index}`);
              if (index === 0) onClearProblem('guardian-required');
            }}
            placeholder={$t('checkin.parentFirstNamePlaceholder')}
            maxlength="255"
            required={firstNameRequired}
            aria-required={firstNameRequired ? 'true' : undefined}
            aria-invalid={firstNameProblem ? 'true' : 'false'}
            aria-describedby={firstNameProblem ? `parent-first-name-problem-${index}` : undefined}
            class={`${inputBase} ${firstNameProblem ? badBorder : okBorder}`}
          />
          {#if firstNameProblem}
            <p
              id={`parent-first-name-problem-${index}`}
              class="mt-1 text-xs text-danger-700"
              data-testid={`parent-first-name-problem-${index}`}
            >
              {firstNameProblem}
            </p>
          {/if}
        </div>
      {:else if key === 'last_name'}
        <div>
          <label for={`parent-last-name-${index}`} class="block text-xs text-neutral-600 mb-1">
            {$t('checkin.parentLastName')}
            {#if required('last_name')}{@render star()}{/if}
          </label>
          <input
            id={`parent-last-name-${index}`}
            type="text"
            bind:value={row.last_name}
            oninput={() => onClearProblem(`parent-last-name-${index}`)}
            placeholder={$t('checkin.parentLastNamePlaceholder')}
            maxlength="255"
            required={required('last_name')}
            aria-required={required('last_name') ? 'true' : undefined}
            aria-invalid={hasProblem(`parent-last-name-${index}`) ? 'true' : 'false'}
            aria-describedby={hasProblem(`parent-last-name-${index}`)
              ? `parent-last-name-problem-${index}`
              : undefined}
            class={`${inputBase} ${hasProblem(`parent-last-name-${index}`) ? badBorder : okBorder}`}
          />
          {#if problemMessage(`parent-last-name-${index}`)}
            <p
              id={`parent-last-name-problem-${index}`}
              class="mt-1 text-xs text-danger-700"
              data-testid={`parent-last-name-problem-${index}`}
            >
              {problemMessage(`parent-last-name-${index}`)}
            </p>
          {/if}
        </div>
      {:else if key === 'phone'}
        <div>
          <label for={`parent-phone-${index}`} class="block text-xs text-neutral-600 mb-1">
            {$t('checkin.parentPhone')}
            {#if required('phone')}{@render star()}{/if}
          </label>
          <input
            id={`parent-phone-${index}`}
            type="tel"
            bind:value={row.phone}
            oninput={() => onClearProblem(`parent-phone-${index}`)}
            placeholder={$t('register.parentPhonePlaceholder')}
            maxlength="50"
            required={required('phone')}
            aria-required={required('phone') ? 'true' : undefined}
            aria-invalid={hasProblem(`parent-phone-${index}`) ? 'true' : 'false'}
            class={`${inputBase} ${hasProblem(`parent-phone-${index}`) ? badBorder : okBorder}`}
            aria-describedby={hasProblem(`parent-phone-${index}`)
              ? `parent-phone-problem-${index}`
              : undefined}
          />
          {#if problemMessage(`parent-phone-${index}`)}
            <p
              id={`parent-phone-problem-${index}`}
              class="mt-1 text-xs text-danger-700"
              data-testid={`parent-phone-problem-${index}`}
            >
              {problemMessage(`parent-phone-${index}`)}
            </p>
          {/if}
        </div>
      {:else if key === 'email'}
        <div>
          <label for={`parent-email-${index}`} class="block text-xs text-neutral-600 mb-1">
            {$t('checkin.parentEmail')}
            {#if required('email')}{@render star()}{/if}
          </label>
          <input
            id={`parent-email-${index}`}
            type="email"
            bind:value={row.email}
            oninput={() => onClearProblem(`parent-email-${index}`)}
            placeholder={$t('checkin.parentEmailPlaceholder')}
            maxlength="254"
            required={required('email')}
            aria-required={required('email') ? 'true' : undefined}
            aria-invalid={hasProblem(`parent-email-${index}`) ? 'true' : 'false'}
            aria-describedby={hasProblem(`parent-email-${index}`)
              ? `parent-email-problem-${index}`
              : undefined}
            class={`${inputBase} ${hasProblem(`parent-email-${index}`) ? badBorder : okBorder}`}
          />
          {#if problemMessage(`parent-email-${index}`)}
            <p
              id={`parent-email-problem-${index}`}
              class="mt-1 text-xs text-danger-700"
              data-testid={`parent-email-problem-${index}`}
            >
              {problemMessage(`parent-email-${index}`)}
            </p>
          {/if}
        </div>
      {:else if key === 'relationship_type'}
        <div>
          <label for={`parent-relationship-${index}`} class="block text-xs text-neutral-600 mb-1">
            {$t('checkin.relationshipType')}
            {#if required('relationship_type')}{@render star()}{/if}
          </label>
          <select
            id={`parent-relationship-${index}`}
            bind:value={row.relationship_type}
            required={required('relationship_type')}
            aria-required={required('relationship_type') ? 'true' : undefined}
            aria-invalid={relationshipMissing ? 'true' : 'false'}
            aria-describedby={relationshipMissing ? `parent-relationship-missing-${index}` : undefined}
            class={`${inputBase} ${relationshipMissing ? badBorder : okBorder}`}
            data-testid={`parent-relationship-${index}`}
          >
            <option value="">{$t('register.relationshipPlaceholder')}</option>
            <option value="MOM">{$t('checkin.relationshipMom')}</option>
            <option value="DAD">{$t('checkin.relationshipDad')}</option>
            <option value="GUARDIAN">{$t('checkin.relationshipGuardian')}</option>
            <option value="OTHER">{$t('checkin.relationshipOther')}</option>
          </select>
          {#if relationshipMissing}
            <p
              id={`parent-relationship-missing-${index}`}
              class="mt-1 text-xs text-danger-700"
              role="alert"
              data-testid={`parent-relationship-missing-${index}`}
            >
              {$t('register.relationshipRequiredCaption')}
            </p>
          {/if}
        </div>
      {/if}
    {:else if key === 'first_name' || key === 'last_name'}
      {@const isFirst = key === 'first_name'}
      {@const nameKey = isFirst ? 'first_name' : 'last_name'}
      <div>
        <label
          for={`child-${isFirst ? 'first' : 'last'}-name-${index}`}
          class="block text-xs text-neutral-600 mb-1"
        >
          {$t(isFirst ? 'checkin.childFirstName' : 'checkin.childLastName')}
          {#if required(key)}{@render star()}{/if}
        </label>
        <input
          id={`child-${isFirst ? 'first' : 'last'}-name-${index}`}
          type="text"
          bind:value={row[nameKey]}
          oninput={() => onClearProblem(`child-info-${index}`)}
          placeholder={$t(isFirst ? 'checkin.childFirstNamePlaceholder' : 'checkin.childLastNamePlaceholder')}
          maxlength="255"
          aria-invalid={hasProblem(`child-info-${index}`) ? 'true' : 'false'}
          class={`${inputBase} ${hasProblem(`child-info-${index}`) ? badBorder : okBorder}`}
          required={required(key)}
        />
      </div>
    {:else if key === 'birthdate'}
      <div>
        <label for={`child-birthdate-${index}`} class="block text-xs text-neutral-600 mb-1">
          {$t('checkin.childBirthdate')}
          {#if required('birthdate')}{@render star()}{/if}
        </label>
        <input
          id={`child-birthdate-${index}`}
          type="date"
          bind:value={row.birthdate}
          onchange={(e) => {
            onBirthdateChange?.(e);
            onClearProblem(`child-info-${index}`);
          }}
          lang={$locale === 'sv' ? 'sv-SE' : 'en-US'}
          max={maxBirthdate}
          min={minBirthdate}
          aria-invalid={row.birthdateRangeInvalid || hasProblem(`child-info-${index}`)
            ? 'true'
            : 'false'}
          aria-describedby={row.birthdateRangeInvalid ? `child-birthdate-invalid-${index}` : undefined}
          class={`${inputBase} ${
            row.birthdateRangeInvalid || hasProblem(`child-info-${index}`) ? badBorder : okBorder
          }`}
          required={required('birthdate')}
        />
        <p class="mt-1 text-xs text-neutral-500">{$t('register.birthdateFormatHint')}</p>
        {#if row.birthdateRangeInvalid}
          <p
            id={`child-birthdate-invalid-${index}`}
            class="mt-1 text-xs font-medium text-danger-700"
            role="alert"
            data-testid={`child-birthdate-invalid-${index}`}
          >
            {$t('register.birthdateInvalid')}
          </p>
        {:else if birthdateProse}
          <p
            class="mt-1 text-xs font-medium text-neutral-700"
            data-testid={`child-birthdate-prose-${index}`}
          >
            {birthdateProse}
          </p>
        {/if}
      </div>
    {/if}
  {/each}
{/snippet}

{#if group === 'parent'}
  <div class="grid grid-cols-2 gap-2">
    {@render personFields()}
  </div>
  {@render middle?.()}
  {#if showConsent}
    <div class="mt-2">
      {@render consent()}
    </div>
  {/if}
{:else}
  <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
    {@render personFields()}
    {@render middle?.()}
    {#if showConsent}
      <div class="md:col-span-2">
        {@render consent()}
      </div>
    {/if}
  </div>
{/if}
