/** Edit form rules for a feature request card: limits, checks and the Confirm payload. */
import { describe, it, expect } from 'vitest';
import { checkForm, editsFrom, fieldIdOf, fieldOfPath, formFrom, FEATURE_LIMITS, type FeatureForm } from './featureRequest';
import type { FeatureRequestCard } from './types';

const form = (over: Partial<FeatureForm> = {}): FeatureForm => ({
  title: 'Family price',
  problem: 'Families want one price.',
  desired: 'One price for a group.',
  tried: ['Two tickets'],
  used: 'A code per family',
  cost: 'extra_steps',
  ...over
});

const card = (over: Partial<FeatureRequestCard> = {}): FeatureRequestCard => ({
  id: 'FR-3',
  title: 'Family price',
  problem: 'Families want one price.',
  desired: 'One price for a group.',
  workaround: { used: 'A code per family', cost: 'extra_steps' },
  matches_existing: null,
  tried: ['Two tickets'],
  touches: ['cap:family_groups'],
  severity: 'friction',
  brief_fragment: null,
  ...over
});

describe('checkForm', () => {
  it('accepts a form at the limits, counted in characters', () => {
    expect(
      checkForm(
        form({
          title: 'x'.repeat(FEATURE_LIMITS.title),
          problem: 'x'.repeat(FEATURE_LIMITS.problem),
          desired: 'x'.repeat(FEATURE_LIMITS.desired),
          tried: ['x'.repeat(FEATURE_LIMITS.tried)],
          used: 'x'.repeat(FEATURE_LIMITS.used)
        }),
        true
      )
    ).toEqual([]);
  });

  it('asks for the required text fields', () => {
    expect(checkForm(form({ title: '   ', problem: '' }), true)).toEqual([
      { field: 'title', code: 'required' },
      { field: 'problem', code: 'required' }
    ]);
  });

  it('flags one over-long field with its limit', () => {
    expect(checkForm(form({ problem: 'x'.repeat(FEATURE_LIMITS.problem + 1) }), true)).toEqual([
      { field: 'problem', code: 'tooLong', max: 600 }
    ]);
  });

  it('counts code points, the way the server does', () => {
    // 100 emoji are 200 UTF-16 units but 100 characters.
    expect(checkForm(form({ title: '🙂'.repeat(FEATURE_LIMITS.title) }), true)).toEqual([]);
    expect(checkForm(form({ title: '🙂'.repeat(FEATURE_LIMITS.title + 1) }), true)).toEqual([
      { field: 'title', code: 'tooLong', max: 100 }
    ]);
  });

  it('checks each tried item and names its index', () => {
    expect(checkForm(form({ tried: ['ok', '', 'y'.repeat(301)] }), true)).toEqual([
      { field: 'tried.1', code: 'required' },
      { field: 'tried.2', code: 'tooLong', max: 300 }
    ]);
  });

  it('checks the workaround text only when the card has a workaround', () => {
    expect(checkForm(form({ used: '' }), true)).toEqual([{ field: 'used', code: 'required' }]);
    expect(checkForm(form({ used: '' }), false)).toEqual([]);
  });
});

describe('editsFrom', () => {
  it('sends the trimmed edited fields and the workaround with its cost', () => {
    expect(
      editsFrom(form({ title: '  Family price  ', cost: 'wrong_result' }), true)
    ).toEqual({
      title: 'Family price',
      problem: 'Families want one price.',
      desired: 'One price for a group.',
      tried: ['Two tickets'],
      workaround: { used: 'A code per family', cost: 'wrong_result' }
    });
  });

  it('leaves the workaround out when the card has none', () => {
    expect(editsFrom(form(), false)).not.toHaveProperty('workaround');
  });
});

describe('formFrom', () => {
  it('copies the stored text, with no workaround defaults when there is none', () => {
    expect(formFrom(card())).toMatchObject({
      title: 'Family price',
      tried: ['Two tickets'],
      used: 'A code per family',
      cost: 'extra_steps'
    });
    expect(formFrom(card({ workaround: null, tried: [] }))).toMatchObject({ used: '', cost: 'none', tried: [] });
  });
});

describe('fieldOfPath and ids', () => {
  it('maps server paths onto the form fields, and leaves unknown ones unnamed', () => {
    expect(fieldOfPath('title')).toBe('title');
    expect(fieldOfPath('workaround.used')).toBe('used');
    expect(fieldOfPath('tried[2]')).toBe('tried');
    expect(fieldOfPath('touches')).toBeNull();
  });

  it('builds field ids from the card id prefix', () => {
    expect(fieldIdOf('fr-FR-3', 'tried.0')).toBe('fr-FR-3-tried-0');
    expect(fieldIdOf('fr-FR-3', 'cost')).toBe('fr-FR-3-cost');
  });
});
