<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { Family, Child, TicketType, Session, FamilyApiResponse } from '$lib/checkin/types';

  // Import shared UI components
  import { PageHeader, StickySearchBox, EmptyState, Alert, Icon } from '$lib/components/ui';

  // Import checkin-specific components
  import SessionIndicator from '$lib/components/checkin/SessionIndicator.svelte';
  import SuccessToast from '$lib/components/checkin/SuccessToast.svelte';
  import CheckinExpandableTable from '$lib/components/checkin/CheckinExpandableTable.svelte';
  import AddFamilyPanel from '$lib/components/checkin/AddFamilyPanel.svelte';
  import SessionSelector from '$lib/components/SessionSelector.svelte';
  import QrScannerOverlay from '$lib/components/checkin/QrScannerOverlay.svelte';

  // Import stores and utilities
  import {
    createUndoAction,
    removeUndoAction,
    getRemainingTime,
    getFamilyUndoActions,
    undoActionsWithTick,
    cleanup as cleanupUndoTimer,
  } from '$lib/checkin/stores/undoTimer';
  import { getVisibleFamilies } from '$lib/checkin/utils/familyVisibility';
  import { mergeFamilies, transformFamily } from '$lib/checkin/utils/mergeFamilies';

  // Import API services
  import { checkinApi, checkInApi, ticketApi, printingApi } from '$lib/api/services';
  import type { ApiError } from '$lib/api/client';
  import { websocketStore } from '$lib/stores/websocket';
  import type { WebSocketMessage, Printer } from '$lib/api/types';

  // ============================================================================
  // HELPER FUNCTIONS - Transform API responses to frontend types
  // ============================================================================

  function transformFamilyResponse(apiFamily: FamilyApiResponse): Family {
    return transformFamily(apiFamily, activeSession);
  }

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  let families = $state<Family[]>([]);
  let activeSession = $state<Session | null>(null);
  let activeSessions = $state<Session[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let searchQuery = $state('');
  let expandedChildId = $state<string | null>(null);
  let showAddPanel = $state(false);
  let successToast = $state<string | null>(null);
  let errorToast = $state<string | null>(null);
  let showCheckedInFamilies = $state(false);
  let showSessionSelector = $state(false);
  let showQrScanner = $state(false);
  let highlightedFamilyId = $state<string | null>(null);
  let supervisedState = $state<Record<string, boolean>>({});

  // Printer / auto-print state
  let printers = $state<Printer[]>([]);
  let selectedPrinterUUID = $state<string>('');
  let autoPrintEnabled = $state<boolean>(false);
  let printersLoaded = $state(false);

  // Subscribe to undo timer store for reactivity
  // Use $derived with $ prefix for proper Svelte 5 store auto-subscription
  let undoActionsData = $derived($undoActionsWithTick);
  let undoActions = $derived(undoActionsData.actions);

  // ============================================================================
  // DATA LOADING
  // ============================================================================

  async function loadFamilies() {
    try {
      loading = true;
      error = null;
      const response = await checkinApi.getFamilies();
      families = mergeFamilies(families, response, activeSession);
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to load families';
      console.error('Error loading families:', err);
    } finally {
      loading = false;
    }
  }

  async function loadActiveSession() {
    try {
      const sessions = await checkinApi.getActiveSessions();
      activeSessions = sessions;
      if (sessions.length > 0) {
        activeSession = sessions[0]; // Use the first active session
      } else {
        error = 'No active session found';
      }
    } catch (err) {
      const apiError = err as ApiError;
      console.error('Error loading active session:', err);
      // Don't set error state here, as it's not critical
    }
  }

  async function loadPrinters() {
    try {
      const result = await printingApi.getPrinters();
      printers = result;
      // Restore saved selection if still valid
      const saved = localStorage.getItem('selectedPrinterUUID') || '';
      if (saved && result.some((p) => p.id === saved)) {
        selectedPrinterUUID = saved;
      } else if (result.length > 0) {
        selectedPrinterUUID = result[0].id;
      }
      autoPrintEnabled = localStorage.getItem('autoPrintEnabled') === 'true';
    } catch (err) {
      console.error('Error loading printers:', err);
    } finally {
      printersLoaded = true;
    }
  }

  // Load data on mount
  onMount(async () => {
    // Load initial data - await to ensure loading state is properly managed
    await Promise.all([loadFamilies(), loadActiveSession(), loadPrinters()]);

    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    const unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Return cleanup function
    return () => {
      unsubscribe();
    };
  });

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  // Helper to get current time formatted
  function getCurrentTime(): string {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  // Helper to format ISO timestamp to local time string
  function formatTime(isoTimestamp: string): string {
    return new Date(isoTimestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  // Track children we've recently checked in to avoid reloading on our own actions
  let recentlyCheckedInChildren = $state<Set<string>>(new Set());

  // Track children we've recently undone to avoid reloading on our own actions
  let recentlyUndoneChildren = $state<Set<string>>(new Set());

  // Handle WebSocket messages for real-time updates
  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === 'child_checked_in') {
      const childId = message.data?.child_id;

      // Only reload if this wasn't our own check-in action
      // This preserves local checkInActionId for undo timers
      if (childId && recentlyCheckedInChildren.has(childId)) {
        // We triggered this - remove from our tracking set
        recentlyCheckedInChildren.delete(childId);
        recentlyCheckedInChildren = new Set(recentlyCheckedInChildren);
        return;
      }

      // Another station checked in a child - update incrementally
      if (childId && message.data?.record_id && message.data?.check_in_time) {
        // Try to find and update the child locally
        let childFound = false;
        families = families.map((fam) => {
          let updated = false;
          const updatedChildren = fam.children.map((child) => {
            if (child.id === childId) {
              childFound = true;
              updated = true;
              // Only update if there's no local undo action
              // (don't overwrite our own check-ins that have active undo)
              if (!child.checkInActionId) {
                return {
                  ...child,
                  checkedIn: true,
                  checkInTime: formatTime(message.data.check_in_time),
                  checkInRecordId: message.data.record_id,
                  // checkInActionId: intentionally undefined - no undo for remote actions
                };
              }
            }
            return child;
          });

          if (updated) {
            return { ...fam, children: updatedChildren };
          }
          return fam;
        });

        // Fallback: if child not found, reload all data
        if (!childFound) {
          console.warn(`Child ${childId} not found locally, reloading families`);
          loadFamilies();
        }
      }
    } else if (message.type === 'child_checked_out') {
      const childId = message.data?.child_id;

      if (childId) {
        // Try to find and update the child locally
        let childFound = false;
        families = families.map((fam) => {
          let updated = false;
          const updatedChildren = fam.children.map((child) => {
            if (child.id === childId) {
              childFound = true;
              updated = true;
              // Clear check-in state
              return {
                ...child,
                checkedIn: false,
                checkInTime: undefined,
                checkInActionId: undefined,
                checkInRecordId: undefined,
              };
            }
            return child;
          });

          if (updated) {
            return { ...fam, children: updatedChildren };
          }
          return fam;
        });

        // Fallback: if child not found, reload all data
        if (!childFound) {
          console.warn(`Child ${childId} not found locally, reloading families`);
          loadFamilies();
        }
      }
    } else if (message.type === 'checkin_undone') {
      const childId = message.data?.child_id;

      // Only process if this wasn't our own undo action
      // This preserves local state for our own undos
      if (childId && recentlyUndoneChildren.has(childId)) {
        // We triggered this - remove from our tracking set
        recentlyUndoneChildren.delete(childId);
        recentlyUndoneChildren = new Set(recentlyUndoneChildren);
        return;
      }

      if (childId) {
        // Another station undid a check-in - update incrementally
        let childFound = false;
        families = families.map((fam) => {
          let updated = false;
          const updatedChildren = fam.children.map((child) => {
            if (child.id === childId) {
              childFound = true;
              updated = true;
              // Clear check-in state unconditionally for remote undo events
              return {
                ...child,
                checkedIn: false,
                checkInTime: undefined,
                checkInActionId: undefined,
                checkInRecordId: undefined,
              };
            }
            return child;
          });

          if (updated) {
            return { ...fam, children: updatedChildren };
          }
          return fam;
        });

        // Fallback: if child not found, reload all data
        if (!childFound) {
          console.warn(`Child ${childId} not found locally, reloading families`);
          loadFamilies();
        }
      }
    } else if (message.type === 'session_started' || message.type === 'session_ended') {
      // Session changes are rare and affect overall state, reload everything
      loadFamilies();
      loadActiveSession();
    } else if (message.type === 'printer_status_changed' || message.type === 'printer_registered') {
      const { uuid, name, is_online } = message.data;
      const existing = printers.find((p) => p.id === uuid);
      if (existing) {
        printers = printers.map((p) =>
          p.id === uuid ? { ...p, name, is_online } : p
        );
      } else if (is_online) {
        printers = [...printers, { id: uuid, name, is_online }];
      }
    }
  }

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================

  // Filter visible families based on search and visibility rules
  const visibleFamilies = $derived.by(() => {
    // If showCheckedInFamilies is enabled, show all families (sorted alphabetically)
    // Otherwise, apply the standard visibility filtering
    let filtered = showCheckedInFamilies
      ? [...families].sort((a, b) => a.name.localeCompare(b.name))
      : getVisibleFamilies(families, undoActions);

    // Always include a highlighted family (e.g. QR-scanned) even if it would normally be hidden
    if (highlightedFamilyId && !filtered.some((f) => f.id === highlightedFamilyId)) {
      const highlightedFamily = families.find((f) => f.id === highlightedFamilyId);
      if (highlightedFamily) {
        filtered = [highlightedFamily, ...filtered];
      }
    }

    if (!searchQuery) return filtered;

    const query = searchQuery.toLowerCase();
    return filtered.filter(
      (family) =>
        family.name.toLowerCase().includes(query) ||
        family.children.some((child) => child.name.toLowerCase().includes(query))
    );
  });

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Cleanup on destroy
  onDestroy(() => {
    cleanupUndoTimer();
    websocketStore.disconnect();
  });

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  // Check in individual child
  async function checkInChild(familyId: string, childId: string) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    try {
      // Track this child to prevent WebSocket reload from clobbering local state
      recentlyCheckedInChildren.add(childId);
      recentlyCheckedInChildren = new Set(recentlyCheckedInChildren);

      // Create undo action
      const actionId = createUndoAction(familyId, [childId]);
      const checkInTime = getCurrentTime();

      // Call API to check in the child
      const checkInRecord = await checkinApi.checkIn({
        child: childId,
        session: activeSession.id,
        supervised: supervisedState[childId] || false,
      });

      // Auto-print label if enabled
      if (autoPrintEnabled && printers.length > 0) {
        try {
          await printingApi.createJob({
            checkin_id: checkInRecord.id,
            printer_id: selectedPrinterUUID || undefined,
          });
        } catch (printErr) {
          console.error('Auto-print job creation failed:', printErr);
        }
      }

      // Update local state optimistically
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((child) => {
            if (child.id !== childId) return child;
            return {
              ...child,
              checkedIn: true,
              checkInTime,
              checkInActionId: actionId,
              checkInRecordId: checkInRecord.id, // Store the backend record ID
            };
          }),
        };
      });

      const family = families.find((f) => f.id === familyId);
      const child = family?.children.find((c) => c.id === childId);
      if (child) {
        successToast = $_('checkin.successCheckedIn', { values: { name: child.name } });
      }

      // Close expansion if open
      expandedChildId = null;
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to check in child';
      console.error('Error checking in child:', err);
    }
  }

  // Check in entire family
  async function checkInFamily(familyId: string) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    const childIdsToCheckIn = family.children
      .filter((c) => !c.checkedIn && c.ticket !== 'none')
      .map((c) => c.id);

    if (childIdsToCheckIn.length === 0) return;

    try {
      // Track all children to prevent WebSocket reload from clobbering local state
      for (const childId of childIdsToCheckIn) {
        recentlyCheckedInChildren.add(childId);
      }
      recentlyCheckedInChildren = new Set(recentlyCheckedInChildren);

      // Check in all children and collect their record IDs
      const checkInRecords = await Promise.all(
        childIdsToCheckIn.map((childId) =>
          checkinApi.checkIn({
            child: childId,
            session: activeSession.id,
            supervised: supervisedState[childId] || false,
          })
        )
      );

      // Map child IDs to record IDs
      const recordIdMap = new Map(
        checkInRecords.map((record) => [record.child, record.id])
      );

      // Auto-print labels if enabled
      if (autoPrintEnabled && printers.length > 0) {
        for (const record of checkInRecords) {
          try {
            await printingApi.createJob({
              checkin_id: record.id,
              printer_id: selectedPrinterUUID || undefined,
            });
          } catch (printErr) {
            console.error('Auto-print job creation failed:', printErr);
          }
        }
      }

      const actionId = createUndoAction(familyId, childIdsToCheckIn);
      const checkInTime = getCurrentTime();

      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          lastCheckInTime: Date.now(),
          children: fam.children.map((child) => {
            if (!childIdsToCheckIn.includes(child.id)) return child;
            return {
              ...child,
              checkedIn: true,
              checkInTime,
              checkInActionId: actionId,
              checkInRecordId: recordIdMap.get(child.id), // Store the backend record ID
            };
          }),
        };
      });

      const count = childIdsToCheckIn.length;
      const childrenLabel = count === 1 ? $_('checkin.child') : $_('checkin.children');
      successToast = $_('checkin.successFamilyCheckedIn', {
        values: {
          family: family.name,
          count: count,
          childrenLabel: childrenLabel,
        },
      });
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to check in family';
      console.error('Error checking in family:', err);
    }
  }

  // Undo individual child check-in
  async function undoChildCheckIn(familyId: string, childId: string) {
    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);

    if (!child?.checkInActionId || !child?.checkInRecordId) {
      return;
    }

    try {
      // Track this child to prevent WebSocket reload from clobbering local state
      recentlyUndoneChildren.add(childId);
      recentlyUndoneChildren = new Set(recentlyUndoneChildren);

      // Call backend undo endpoint
      await checkInApi.undo(child.checkInRecordId);

      // Remove undo action from timer store
      removeUndoAction(child.checkInActionId);

      // Update local state
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((c) => {
            if (c.id !== childId) return c;
            return {
              ...c,
              checkedIn: false,
              checkInTime: undefined,
              checkInActionId: undefined,
              checkInRecordId: undefined,
            };
          }),
        };
      });

      if (child) {
        successToast = $_('checkin.checkInUndone', { values: { name: child.name } });
      }
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to undo check-in';
      console.error('Error undoing check-in:', err);
    }
  }

  // Undo family check-in
  async function undoFamilyCheckIn(familyId: string) {
    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    // Find all undo actions for this family
    const familyActions = getFamilyUndoActions(familyId);
    if (familyActions.length === 0) return;

    // Get the most recent family action (should have multiple children)
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    if (!familyAction) return;

    try {
      // Find all children affected by this family action
      const affectedChildren = family.children.filter(
        (c) => familyAction.childIds.includes(c.id) && c.checkInActionId === familyAction.id
      );

      // Track all children to prevent WebSocket reload from clobbering local state
      for (const child of affectedChildren) {
        recentlyUndoneChildren.add(child.id);
      }
      recentlyUndoneChildren = new Set(recentlyUndoneChildren);

      // Call backend undo endpoint for each child
      await Promise.all(
        affectedChildren
          .filter((c) => c.checkInRecordId)
          .map((c) => checkInApi.undo(c.checkInRecordId!))
      );

      // Remove undo action from timer store
      removeUndoAction(familyAction.id);

      // Update local state - undo all children affected by this action
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((c) => {
            if (
              familyAction.childIds.includes(c.id) &&
              c.checkInActionId === familyAction.id
            ) {
              return {
                ...c,
                checkedIn: false,
                checkInTime: undefined,
                checkInActionId: undefined,
                checkInRecordId: undefined,
              };
            }
            return c;
          }),
        };
      });

      successToast = $_('checkin.familyCheckInUndone', { values: { name: family.name } });
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to undo family check-in';
      console.error('Error undoing family check-in:', err);
    }
  }

  async function handleQrScan(code: string) {
    showQrScanner = false;
    try {
      const apiFamily = await checkinApi.lookupByTicket(code);
      const found = families.find((f) => f.id === apiFamily.id);
      if (found) {
        highlightedFamilyId = found.id;
      } else {
        families = mergeFamilies(families, [apiFamily], activeSession);
        highlightedFamilyId = apiFamily.id;
      }
      // Filter the list down to the scanned family instead of merely
      // highlighting it within the full list. Reusing the search box keeps the
      // filter visible and clearable. highlightedFamilyId stays set so the
      // visibleFamilies force-include surfaces the family even when it would
      // normally be hidden (e.g. already fully checked in); it's cleared as
      // soon as the user touches the search box (see onInput below).
      searchQuery = apiFamily.display_name;
    } catch (err) {
      const apiError = err as ApiError;
      const msg = apiError.status === 404 ? $_('checkin.qrNotFound') : $_('checkin.qrLookupError');
      errorToast = msg;
      setTimeout(() => { if (errorToast === msg) errorToast = null; }, 4000);
    }
  }

  // Handle session change button click
  function handleChangeSession() {
    showSessionSelector = true;
  }

  // Handle session selection from modal
  function handleSessionSelect(session: Session) {
    activeSession = session;
    showSessionSelector = false;
    loadFamilies();
  }

  // Assign ticket and check in child
  async function assignTicketAndCheckIn(
    familyId: string,
    childId: string,
    ticketType: TicketType
  ) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    try {
      // Assign the ticket via API based on ticket type
      if (ticketType === 'event') {
        await ticketApi.assignEventTicket({
          child: childId,
          event: activeSession.event,
        });
      } else if (ticketType === 'session') {
        await ticketApi.assignSessionTicket({
          child: childId,
          session: activeSession.id,
        });
      }

      // Update local state
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((child) => {
            if (child.id !== childId) return child;
            return { ...child, ticket: ticketType, ticket_type: ticketType };
          }),
        };
      });

      // Then check in the child
      await checkInChild(familyId, childId);
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to assign ticket';
      console.error('Error assigning ticket:', err);
    }
  }

  // Add new family
  async function handleAddFamily(data: {
    familyName: string;
    children: Array<{
      first_name: string;
      last_name: string;
      birthdate: string;
      allergies: string;
      notes: string;
    }>;
    ticketType: TicketType;
    parents: Array<{
      name: string;
      phone: string;
      email: string;
      relationship_type: string;
    }>;
  }) {
    try {
      // Create family via API
      const newFamily = await checkinApi.createFamily({
        last_name: data.familyName,
        parents: data.parents,
        children: data.children.map((c) => ({
          first_name: c.first_name.trim(),
          last_name: c.last_name.trim(),
          birthdate: c.birthdate.trim(),
          allergies: c.allergies.trim() || undefined,
          notes: c.notes.trim() || undefined,
        })),
      });

      // Transform and add to local state
      const transformedFamily = transformFamilyResponse(newFamily);

      // Assign tickets to children if needed
      if (data.ticketType !== 'none' && activeSession) {
        for (const child of transformedFamily.children) {
          if (data.ticketType === 'event') {
            await ticketApi.assignEventTicket({
              child: child.id,
              event: activeSession.event,
            });
          } else if (data.ticketType === 'session') {
            await ticketApi.assignSessionTicket({
              child: child.id,
              session: activeSession.id,
            });
          }
          // Update ticket type in local state
          child.ticket = data.ticketType;
          child.ticket_type = data.ticketType;
        }
      }

      families = [...families, transformedFamily].sort((a, b) =>
        a.name.localeCompare(b.name)
      );
      showAddPanel = false;

      const count = transformedFamily.children.length;
      const childrenLabel = count === 1 ? $_('checkin.child') : $_('checkin.children');
      successToast = $_('checkin.familyAdded', {
        values: {
          familyName: data.familyName,
          count: count,
          childrenLabel: childrenLabel,
        },
      });
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to create family';
      console.error('Error creating family:', err);
    }
  }
</script>

<svelte:head>
  <title>{$_('checkin.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-3 md:p-5">
    {#if loading}
      <div class="text-center py-12">
        <p class="text-slate-600">{$_('common.loading')}</p>
      </div>
    {:else if error}
      <Alert type="error" class="mb-4">
        {error}
        <div class="mt-2">
          <button
            onclick={() => {
              error = null;
              loadFamilies();
            }}
            class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            {$_('common.retry')}
          </button>
        </div>
      </Alert>
    {:else}
      <!-- Session Indicator -->
      <SessionIndicator
        eventName={activeSession?.event_name || 'No Event'}
        sessionName={activeSession?.name || 'No Active Session'}
        sessionTime={activeSession
          ? `${new Date(activeSession.start_time).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            })} - ${activeSession.end_time ? new Date(activeSession.end_time).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }) : 'Open'}`
          : ''}
        showChangeSession={activeSessions.length > 1}
        onChangeSession={handleChangeSession}
        onAddFamily={() => (showAddPanel = true)}
      />

    <!-- Printer Selector (only shown when printers exist) -->
    {#if printersLoaded && printers.length > 0}
      <div class="mb-3 flex items-center gap-3 bg-white rounded-card border border-slate-200 px-4 py-2 text-sm">
        <label class="flex items-center gap-2 cursor-pointer flex-1">
          <input
            type="checkbox"
            bind:checked={autoPrintEnabled}
            onchange={() => localStorage.setItem('autoPrintEnabled', String(autoPrintEnabled))}
            class="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
          />
          <span class="font-medium text-slate-700">{$_('printing.autoPrint')}</span>
        </label>
        {#if autoPrintEnabled}
          <select
            bind:value={selectedPrinterUUID}
            onchange={() => localStorage.setItem('selectedPrinterUUID', selectedPrinterUUID)}
            class="text-sm border border-slate-300 rounded px-2 py-1 bg-white focus:ring-blue-500 focus:border-blue-500"
          >
            {#each printers as printer}
              <option value={printer.id}>
                {printer.name}{printer.is_online ? '' : ' (offline)'}
              </option>
            {/each}
          </select>
        {/if}
      </div>
    {/if}

    <!-- Add Family Panel -->
    {#if showAddPanel}
      <AddFamilyPanel
        onAdd={handleAddFamily}
        onClose={() => (showAddPanel = false)}
      />
    {/if}

    <!-- Session Selector Modal -->
    <SessionSelector
      show={showSessionSelector}
      sessions={activeSessions}
      currentSession={activeSession}
      onSelect={handleSessionSelect}
      onClose={() => showSessionSelector = false}
    />

    <!-- Header -->
    <PageHeader title={$_('checkin.title')} />

    <!-- Sticky Search Box -->
    <StickySearchBox
      bind:value={searchQuery}
      placeholder={$_('checkin.searchPlaceholder')}
      onInput={() => (highlightedFamilyId = null)}
      onQrScan={() => (showQrScanner = true)}
    />

    <div class="mb-4 flex items-left justify-between text-sm">
    <!-- Stats Header -->
      <span class="text-slate-600" data-testid="family-count-text">
        {visibleFamilies.length}{' '}
        {visibleFamilies.length === 1 ? $_('common.family') : $_('common.families')}
        {searchQuery && ` ${$_('checkin.matchingSearch')}`}
      </span>
      <!-- Show Checked-In Families Toggle -->
      <label class="flex items-center gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          bind:checked={showCheckedInFamilies}
          class="w-4 h-4 text-blue-600 bg-white border-slate-300 rounded focus:ring-blue-500 focus:ring-2"
        />
        <span class="text-slate-700">{$_('checkin.showCheckedInFamilies')}</span>
      </label>
    </div>

    <!-- Family List -->
    {#if visibleFamilies.length === 0}
      <EmptyState
        type="empty"
        title={searchQuery
          ? $_('checkin.noFamiliesFound', { values: { query: searchQuery } })
          : $_('checkin.noFamilies')}
      >
        {#snippet icon()}
          <Icon name="users" size="xl" />
        {/snippet}
        {#if searchQuery}
          {#snippet description()}
            <p class="text-sm">{$_('checkin.tryDifferentSearch')}</p>
          {/snippet}
        {/if}
      </EmptyState>
    {:else}
      <CheckinExpandableTable
        families={visibleFamilies}
        onCheckInChild={checkInChild}
        onCheckInFamily={checkInFamily}
        onUndoChild={undoChildCheckIn}
        onUndoFamily={undoFamilyCheckIn}
        onAssignTicket={assignTicketAndCheckIn}
        {getRemainingTime}
        bind:supervisedState
        {expandedChildId}
        onToggleChildExpansion={(childId) => {
          expandedChildId = childId;
        }}
        {searchQuery}
        {highlightedFamilyId}
      />
    {/if}
  {/if}
  </div>
</div>

<!-- QR Scanner Overlay -->
{#if showQrScanner}
  <QrScannerOverlay onScan={handleQrScan} onClose={() => (showQrScanner = false)} />
{/if}

<!-- Success Toast -->
{#if successToast}
  <SuccessToast
    message={successToast}
    onClose={() => {
      successToast = null;
    }}
  />
{/if}

<!-- Error Toast (QR scan misses, etc.) -->
{#if errorToast}
  <div
    class="fixed top-4 right-4 bg-red-50 text-red-700 border border-red-400 px-4 py-3 rounded-card shadow-lg flex items-center gap-3 z-50 animate-slide-in"
    role="alert"
    aria-live="assertive"
  >
    <span class="text-xl flex-shrink-0">✕</span>
    <span class="font-semibold flex-1">{errorToast}</span>
    <button
      type="button"
      class="flex-shrink-0 text-current hover:opacity-70 transition-opacity"
      onclick={() => { errorToast = null; }}
      aria-label="Dismiss"
    >
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>
  </div>
{/if}

<!-- Animations -->
<style>
  :global(.animate-slide-in) {
    animation: slide-in 0.3s ease-out;
  }

  :global(.animate-expand) {
    animation: expand 0.2s ease-out;
  }

  @keyframes slide-in {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes expand {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
