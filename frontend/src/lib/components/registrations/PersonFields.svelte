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

  // The parent text inputs that differ only in these attributes; the ids,
  // test ids and aria attributes derive from the slug.
  const PARENT_TEXT_FIELDS = {
    last_name: {
      slug: 'last-name',
      type: 'text',
      label: 'checkin.parentLastName',
      placeholder: 'checkin.parentLastNamePlaceholder',
      maxlength: 255
    },
    phone: {
      slug: 'phone',
      type: 'tel',
      label: 'checkin.parentPhone',
      placeholder: 'register.parentPhonePlaceholder',
      maxlength: 50
    },
    email: {
      slug: 'email',
      type: 'email',
      label: 'checkin.parentEmail',
      placeholder: 'checkin.parentEmailPlaceholder',
      maxlength: 254
    }
  } as const;
  type ParentTextKey = keyof typeof PARENT_TEXT_FIELDS;
  const isParentTextKey = (key: string): key is ParentTextKey => key in PARENT_TEXT_FIELDS;
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

  // Keys the markup below has no branch for (the health fields) render nothing here.
  const keys = $derived(spec.fields[group].filter((f) => f.visible).map((f) => f.key));

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

{#snippet parentTextField(key: ParentTextKey)}
  {@const f = PARENT_TEXT_FIELDS[key]}
  {@const id = `parent-${f.slug}-${index}`}
  <div>
    <label for={id} class="block text-xs text-neutral-600 mb-1">
      {$t(f.label)}
      {#if required(key)}{@render star()}{/if}
    </label>
    <input
      {id}
      type={f.type}
      bind:value={row[key]}
      oninput={() => onClearProblem(id)}
      placeholder={$t(f.placeholder)}
      maxlength={f.maxlength}
      required={required(key)}
      aria-required={required(key) ? 'true' : undefined}
      aria-invalid={hasProblem(id) ? 'true' : 'false'}
      aria-describedby={hasProblem(id) ? `parent-${f.slug}-problem-${index}` : undefined}
      class={`${inputBase} ${hasProblem(id) ? badBorder : okBorder}`}
    />
    {#if problemMessage(id)}
      <p
        id={`parent-${f.slug}-problem-${index}`}
        class="mt-1 text-xs text-danger-700"
        data-testid={`parent-${f.slug}-problem-${index}`}
      >
        {problemMessage(id)}
      </p>
    {/if}
  </div>
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
      {:else if isParentTextKey(key)}
        {@render parentTextField(key)}
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
