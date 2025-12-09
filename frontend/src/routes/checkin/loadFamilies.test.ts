import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Family, Child, FamilyApiResponse } from '$lib/checkin/types';
import { mergeFamilies } from '$lib/checkin/utils/mergeFamilies';

/**
 * Tests for loadFamilies() in-place merge logic
 *
 * The goal is to merge fresh API data while preserving critical local state:
 * - checkInActionId (for undo timers)
 * - checkInRecordId (for API calls)
 * - checkInTime (formatted display time)
 * - Any UI-specific fields
 */

describe('loadFamilies merge logic', () => {
  let existingFamilies: Family[];
  let apiFamilies: FamilyApiResponse[];

  beforeEach(() => {
    // Setup existing local state with undo timer data
    existingFamilies = [
      {
        id: 'family-1',
        name: 'Smith Family',
        last_name: 'Smith',
        display_name: 'Smith Family',
        children: [
          {
            id: 'child-1',
            name: 'Alice Smith',
            first_name: 'Alice',
            last_name: 'Smith',
            ticket: 'event',
            ticket_type: 'event',
            checkedIn: true,
            checkInTime: '9:15 AM',
            checkInActionId: 'action-uuid-123', // LOCAL STATE - must preserve
            checkInRecordId: 'record-uuid-456', // LOCAL STATE - must preserve
            family: 'family-1',
            qr_token: 'qr-123',
          } as Child,
          {
            id: 'child-2',
            name: 'Bob Smith',
            first_name: 'Bob',
            last_name: 'Smith',
            ticket: 'session',
            ticket_type: 'session',
            checkedIn: false,
            family: 'family-1',
            qr_token: 'qr-124',
          } as Child,
        ],
        parents: [],
      } as Family,
      {
        id: 'family-2',
        name: 'Jones Family',
        last_name: 'Jones',
        display_name: 'Jones Family',
        children: [
          {
            id: 'child-3',
            name: 'Charlie Jones',
            first_name: 'Charlie',
            last_name: 'Jones',
            ticket: 'event',
            ticket_type: 'event',
            checkedIn: false,
            family: 'family-2',
            qr_token: 'qr-125',
          } as Child,
        ],
        parents: [],
      } as Family,
    ];

    // Setup fresh API response (missing local state fields)
    apiFamilies = [
      {
        id: 'family-1',
        last_name: 'Smith',
        display_name: 'Smith Family',
        children: [
          {
            id: 'child-1',
            first_name: 'Alice',
            last_name: 'Smith',
            ticket_type: 'event',
            is_checked_in: true, // Backend reflects check-in
            family: 'family-1',
            qr_token: 'qr-123',
            // Note: API doesn't include checkInActionId, checkInRecordId, checkInTime
          },
          {
            id: 'child-2',
            first_name: 'Bob',
            last_name: 'Smith',
            ticket_type: 'session',
            is_checked_in: false,
            family: 'family-1',
            qr_token: 'qr-124',
          },
        ],
        parents: [],
      },
      {
        id: 'family-2',
        last_name: 'Jones',
        display_name: 'Jones Family',
        children: [
          {
            id: 'child-3',
            first_name: 'Charlie',
            last_name: 'Jones',
            ticket_type: 'event',
            is_checked_in: false,
            family: 'family-2',
            qr_token: 'qr-125',
          },
        ],
        parents: [],
      },
    ] as FamilyApiResponse[];
  });

  it('should preserve checkInActionId for checked-in children', () => {
    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    expect(alice?.checkInActionId).toBe('action-uuid-123');
  });

  it('should preserve checkInRecordId for checked-in children', () => {
    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    expect(alice?.checkInRecordId).toBe('record-uuid-456');
  });

  it('should preserve checkInTime for checked-in children', () => {
    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    expect(alice?.checkInTime).toBe('9:15 AM');
  });

  it('should update backend check-in status from API', () => {
    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    expect(alice?.checkedIn).toBe(true);
  });

  it('should update child properties from fresh API data', () => {
    // Simulate API returning updated allergies
    apiFamilies[0].children[0].allergies = 'Peanuts';

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    expect(alice?.allergies).toBe('Peanuts');
    // But still preserve local state
    expect(alice?.checkInActionId).toBe('action-uuid-123');
  });

  it('should not add local state to non-checked-in children', () => {
    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const bob = merged[0].children.find(c => c.id === 'child-2');
    expect(bob?.checkInActionId).toBeUndefined();
    expect(bob?.checkInRecordId).toBeUndefined();
    expect(bob?.checkInTime).toBeUndefined();
  });

  it('should handle new families from API', () => {
    // Add a new family to API response
    apiFamilies.push({
      id: 'family-3',
      last_name: 'Brown',
      display_name: 'Brown Family',
      children: [
        {
          id: 'child-4',
          first_name: 'Diana',
          last_name: 'Brown',
          ticket_type: 'event',
          is_checked_in: false,
          family: 'family-3',
          qr_token: 'qr-126',
        },
      ],
      parents: [],
    } as FamilyApiResponse);

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    expect(merged).toHaveLength(3);
    expect(merged[2].id).toBe('family-3');
    expect(merged[2].children[0].name).toBe('Diana Brown');
  });

  it('should handle new children in existing family', () => {
    // Add a new child to family-1
    apiFamilies[0].children.push({
      id: 'child-5',
      first_name: 'Eve',
      last_name: 'Smith',
      ticket_type: 'session',
      is_checked_in: false,
      family: 'family-1',
      qr_token: 'qr-127',
    });

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const smithFamily = merged.find(f => f.id === 'family-1');
    expect(smithFamily?.children).toHaveLength(3);

    const eve = smithFamily?.children.find(c => c.id === 'child-5');
    expect(eve?.name).toBe('Eve Smith');
    expect(eve?.checkInActionId).toBeUndefined();
  });

  it('should handle removed families (not in API response)', () => {
    // Remove family-2 from API response
    apiFamilies = apiFamilies.filter(f => f.id !== 'family-2');

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe('family-1');
  });

  it('should handle removed children (not in API response)', () => {
    // Remove child-2 from family-1
    apiFamilies[0].children = apiFamilies[0].children.filter(
      c => c.id !== 'child-2'
    );

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const smithFamily = merged.find(f => f.id === 'family-1');
    expect(smithFamily?.children).toHaveLength(1);
    expect(smithFamily?.children[0].id).toBe('child-1');
  });

  it('should handle empty existing families array', () => {
    const merged = mergeFamilies([], apiFamilies);

    expect(merged).toHaveLength(2);
    expect(merged[0].children[0].checkInActionId).toBeUndefined();
  });

  it('should handle empty API response', () => {
    const merged = mergeFamilies(existingFamilies, []);

    expect(merged).toHaveLength(0);
  });

  it('should preserve multiple children with undo timers', () => {
    // Add undo timer to Bob
    existingFamilies[0].children[1].checkInActionId = 'action-uuid-789';
    existingFamilies[0].children[1].checkInRecordId = 'record-uuid-101';
    existingFamilies[0].children[1].checkInTime = '9:20 AM';
    existingFamilies[0].children[1].checkedIn = true;

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');
    const bob = merged[0].children.find(c => c.id === 'child-2');

    expect(alice?.checkInActionId).toBe('action-uuid-123');
    expect(alice?.checkInTime).toBe('9:15 AM');
    expect(bob?.checkInActionId).toBe('action-uuid-789');
    expect(bob?.checkInTime).toBe('9:20 AM');
  });

  it('should handle child checked out on backend (backend says not checked in)', () => {
    // Local state says Alice is checked in with undo timer
    // But API says she's checked out
    apiFamilies[0].children[0].is_checked_in = false;

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    const alice = merged[0].children.find(c => c.id === 'child-1');

    // Backend state takes precedence for checkedIn status
    expect(alice?.checkedIn).toBe(false);

    // But we still preserve local undo timer state
    // (This allows the undo button to show briefly before timer expires)
    expect(alice?.checkInActionId).toBe('action-uuid-123');
    expect(alice?.checkInRecordId).toBe('record-uuid-456');
  });

  it('should preserve family-level fields from API', () => {
    apiFamilies[0].last_participation_date = '2025-01-15';

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    expect(merged[0].last_participation_date).toBe('2025-01-15');
  });

  it('should maintain family order from API response', () => {
    // Reverse the API order
    apiFamilies.reverse();

    const merged = mergeFamilies(existingFamilies, apiFamilies);

    // Should follow API order (family-2, then family-1)
    expect(merged[0].id).toBe('family-2');
    expect(merged[1].id).toBe('family-1');
  });
});
