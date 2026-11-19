import type {
  RegistrationExtraInfo,
  RegistrationFormField,
  RegistrationFormSpec,
  RegistrationTicketType
} from '$lib/api/types';

// Pure selection helpers for the register page: everything takes the spec
// as an argument, so no form state lives in this module (keeps Vite HMR safe).

export type FieldGroup = 'parent' | 'child';

export interface ExtraSelectionState {
  selected: boolean;
  choiceId: string;
  quantity: number;
}

type MaybeSpec = RegistrationFormSpec | null | undefined;

export function applicableTicketTypes(spec: MaybeSpec, isChild: boolean): RegistrationTicketType[] {
  if (!spec) return [];
  const kind = isChild ? 'child' : 'parent';
  return spec.ticket_types.filter((tt) => tt.applies_to === kind || tt.applies_to === 'either');
}

export function applicablePersonExtras(spec: MaybeSpec, isChild: boolean): RegistrationExtraInfo[] {
  if (!spec) return [];
  const kind = isChild ? 'child' : 'parent';
  return spec.extras.filter(
    (extra) => extra.per_attendee && (extra.applies_to === kind || extra.applies_to === 'either')
  );
}

export function registrationExtras(spec: MaybeSpec): RegistrationExtraInfo[] {
  return spec ? spec.extras.filter((extra) => !extra.per_attendee) : [];
}

export function fieldFor(
  spec: MaybeSpec,
  group: FieldGroup,
  key: string
): RegistrationFormField | undefined {
  return spec?.fields[group].find((f) => f.key === key);
}

// A field the spec does not list is not asked for.
export function isFieldVisible(spec: MaybeSpec, group: FieldGroup, key: string): boolean {
  return fieldFor(spec, group, key)?.visible ?? false;
}

// A hidden field is never required, whatever its flag says.
export function isFieldRequired(spec: MaybeSpec, group: FieldGroup, key: string): boolean {
  const field = fieldFor(spec, group, key);
  return !!field && field.visible && field.required;
}

export interface PersonSelection {
  ticketTypeId: string;
  extraSelections: Record<string, ExtraSelectionState>;
}

export interface SelectionState<P extends PersonSelection, C extends PersonSelection> {
  spec: RegistrationFormSpec;
  parents: P[];
  children: C[];
  registrationExtraSelections: Record<string, ExtraSelectionState>;
}

export interface ClearedItem {
  kind: 'ticketType' | 'extra' | 'extraChoice';
  name: string;
}

export interface ReconcileResult<P extends PersonSelection, C extends PersonSelection> {
  parents: P[];
  children: C[];
  registrationExtraSelections: Record<string, ExtraSelectionState>;
  cleared: ClearedItem[];
}

// Drops selections that point at ticket types, extras or extra choices the
// new spec no longer offers to that person. Old names come from state.spec,
// since the new one no longer has them. Everything else is left untouched.
export function reconcileSelections<P extends PersonSelection, C extends PersonSelection>(
  state: SelectionState<P, C>,
  newSpec: RegistrationFormSpec
): ReconcileResult<P, C> {
  const cleared: ClearedItem[] = [];
  const note = (item: ClearedItem) => {
    if (!cleared.some((c) => c.kind === item.kind && c.name === item.name)) cleared.push(item);
  };
  const oldExtras = new Map(state.spec.extras.map((e) => [e.id, e]));
  const oldTickets = new Map(state.spec.ticket_types.map((t) => [t.id, t]));

  function reconcileExtras(
    selections: Record<string, ExtraSelectionState>,
    allowed: RegistrationExtraInfo[]
  ): Record<string, ExtraSelectionState> {
    const result: Record<string, ExtraSelectionState> = {};
    for (const [extraId, sel] of Object.entries(selections)) {
      const extra = allowed.find((e) => e.id === extraId);
      if (!extra) {
        // An untouched entry is not a selection worth reporting.
        if (sel.selected || sel.choiceId) {
          note({ kind: 'extra', name: oldExtras.get(extraId)?.name ?? extraId });
        }
        continue;
      }
      if (sel.choiceId && !extra.choices.some((c) => c.id === sel.choiceId)) {
        const label = oldExtras.get(extraId)?.choices.find((c) => c.id === sel.choiceId)?.label;
        note({ kind: 'extraChoice', name: label ? `${extra.name} – ${label}` : extra.name });
        result[extraId] = { ...sel, choiceId: '' };
        continue;
      }
      result[extraId] = sel;
    }
    return result;
  }

  function reconcilePerson<T extends PersonSelection>(person: T, isChild: boolean): T {
    const offered = applicableTicketTypes(newSpec, isChild);
    let ticketTypeId = person.ticketTypeId;
    if (ticketTypeId && !offered.some((tt) => tt.id === ticketTypeId)) {
      note({ kind: 'ticketType', name: oldTickets.get(ticketTypeId)?.name ?? ticketTypeId });
      ticketTypeId = '';
    }
    return {
      ...person,
      ticketTypeId,
      extraSelections: reconcileExtras(
        person.extraSelections,
        applicablePersonExtras(newSpec, isChild)
      )
    };
  }

  return {
    parents: state.parents.map((p) => reconcilePerson(p, false)),
    children: state.children.map((c) => reconcilePerson(c, true)),
    registrationExtraSelections: reconcileExtras(
      state.registrationExtraSelections,
      registrationExtras(newSpec)
    ),
    cleared
  };
}
