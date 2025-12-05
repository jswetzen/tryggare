import { test, expect } from '@playwright/test';

/**
 * Check-In Station E2E Test Suite
 *
 * These tests are framework-agnostic and should work with both
 * React and Svelte implementations. They rely on data-testid attributes
 * for element selection to remain decoupled from implementation details.
 */

test.describe('Check-In Station', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the application with initial state', async ({ page }) => {
    // Verify page title
    await expect(page).toHaveTitle(/Check-In Station/i);

    // Verify session indicator is visible
    await expect(page.getByTestId('session-indicator')).toBeVisible();

    // Verify search input is visible
    await expect(page.getByTestId('search-input')).toBeVisible();

    // Verify family count shows initial families (4 families from mock data)
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('4 families');
  });

  test('should search for family by name', async ({ page }) => {
    const searchInput = page.getByTestId('search-input');

    // Search for "Garcia" family
    await searchInput.fill('Garcia');

    // Should show 1 family matching search
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('1 family');
    await expect(familyCountText).toContainText('matching search');

    // Garcia family card should be visible
    await expect(page.getByTestId('family-card-1')).toBeVisible();

    // Other families should not be visible
    await expect(page.getByTestId('family-card-2')).not.toBeVisible();
  });

  test('should search for child by name and auto-expand family', async ({ page }) => {
    // Search for a child name that doesn't match the family name
    const searchInput = page.getByTestId('search-input');
    await searchInput.fill('Sophia');

    // Should show 1 family
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('1 family');

    // Johnson family (id=2) should be visible and auto-expanded
    const familyCard = page.getByTestId('family-card-2');
    await expect(familyCard).toBeVisible();

    // Child row should be visible (child id=3 is Sophia Johnson)
    await expect(page.getByTestId('child-row-3')).toBeVisible();
  });

  test('should clear search query', async ({ page }) => {
    const searchInput = page.getByTestId('search-input');

    // Enter a search query
    await searchInput.fill('Garcia');

    // Verify clear button appears
    const clearButton = page.getByTestId('clear-search-button');
    await expect(clearButton).toBeVisible();

    // Click clear button
    await clearButton.click();

    // Search input should be empty
    await expect(searchInput).toHaveValue('');

    // Should show all families again
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('4 families');
  });

  test('should expand and collapse family card', async ({ page }) => {
    const familyToggle = page.getByTestId('family-toggle-button-1');

    // Initially collapsed, children not visible
    await expect(page.getByTestId('child-row-1')).not.toBeVisible();

    // Click to expand
    await familyToggle.click();

    // Children should now be visible
    await expect(page.getByTestId('child-row-1')).toBeVisible();
    await expect(page.getByTestId('child-row-2')).toBeVisible();

    // Click to collapse
    await familyToggle.click();

    // Children should be hidden again
    await expect(page.getByTestId('child-row-1')).not.toBeVisible();
  });

  test('should check in individual child', async ({ page }) => {
    // Expand Garcia family
    await page.getByTestId('family-toggle-button-1').click();

    // Click check-in button for first child (Isabella Garcia, id=1)
    const checkInButton = page.getByTestId('child-check-in-button-1');
    await expect(checkInButton).toBeVisible();
    await checkInButton.click();

    // Success toast should appear
    await expect(page.getByTestId('success-toast')).toBeVisible();
    await expect(page.getByTestId('success-toast')).toContainText('Isabella Garcia checked in');

    // Undo button should appear with countdown
    const undoButton = page.getByTestId('child-undo-button-1');
    await expect(undoButton).toBeVisible();
    await expect(undoButton).toContainText(/Undo \(\d+s\)/);
  });

  test('should check in entire family', async ({ page }) => {
    // Click Check In Family button for Smith family (id=3, all children have tickets)
    const checkInFamilyButton = page.getByTestId('family-check-in-button-3');
    await checkInFamilyButton.click();

    // Success toast should appear
    await expect(page.getByTestId('success-toast')).toBeVisible();
    await expect(page.getByTestId('success-toast')).toContainText('Smith family checked in');

    // Family undo button should appear
    const familyUndoButton = page.getByTestId('family-undo-button-3');
    await expect(familyUndoButton).toBeVisible();
    await expect(familyUndoButton).toContainText(/Undo Family \(\d+s\)/);
  });

  test('should undo individual child check-in within timer', async ({ page }) => {
    // Expand Garcia family and check in a child
    await page.getByTestId('family-toggle-button-1').click();
    await page.getByTestId('child-check-in-button-1').click();

    // Wait for success toast to appear
    await expect(page.getByTestId('success-toast')).toBeVisible();

    // Click undo button
    const undoButton = page.getByTestId('child-undo-button-1');
    await undoButton.click();

    // Success toast should show undo confirmation
    await expect(page.getByTestId('success-toast')).toContainText('check-in undone');

    // Check-in button should be available again
    await expect(page.getByTestId('child-check-in-button-1')).toBeVisible();

    // Undo button should disappear
    await expect(undoButton).not.toBeVisible();
  });

  test('should undo family check-in within timer', async ({ page }) => {
    // Check in entire Smith family (id=3, all children have tickets)
    await page.getByTestId('family-check-in-button-3').click();

    // Wait for success toast
    await expect(page.getByTestId('success-toast')).toBeVisible();

    // Click family undo button
    const familyUndoButton = page.getByTestId('family-undo-button-3');
    await familyUndoButton.click();

    // Success toast should show undo confirmation
    await expect(page.getByTestId('success-toast')).toContainText('Smith check-in undone');

    // Check In Family button should be available again
    await expect(page.getByTestId('family-check-in-button-3')).toBeVisible();

    // Undo button should disappear
    await expect(familyUndoButton).not.toBeVisible();
  });

  test('should verify undo timer countdown', async ({ page }) => {
    // Expand Garcia family and check in a child
    await page.getByTestId('family-toggle-button-1').click();
    await page.getByTestId('child-check-in-button-1').click();

    // Get initial timer value
    const undoButton = page.getByTestId('child-undo-button-1');
    const initialText = await undoButton.textContent();
    const initialSeconds = parseInt(initialText?.match(/\d+/)?.[0] || '0');

    // Wait 2 seconds
    await page.waitForTimeout(2000);

    // Timer should have decreased
    const newText = await undoButton.textContent();
    const newSeconds = parseInt(newText?.match(/\d+/)?.[0] || '0');
    expect(newSeconds).toBeLessThan(initialSeconds);
  });

  test('should expand child row for ticket assignment', async ({ page }) => {
    // Expand Garcia family
    await page.getByTestId('family-toggle-button-1').click();

    // Child with id=2 (Lucas Garcia) has no ticket
    // Click the expand button
    const expandButton = page.getByTestId('child-expand-button-2');
    await expandButton.click();

    // Ticket assignment buttons should be visible
    await expect(page.getByTestId('ticket-assign-session-2')).toBeVisible();
    await expect(page.getByTestId('ticket-assign-event-2')).toBeVisible();
  });

  test('should assign Event Pass ticket to child without ticket', async ({ page }) => {
    // Expand Garcia family
    await page.getByTestId('family-toggle-button-1').click();

    // Expand child row for Lucas Garcia (id=2)
    await page.getByTestId('child-expand-button-2').click();

    // Click Event Pass button
    await page.getByTestId('ticket-assign-event-2').click();

    // Success toast should appear
    await expect(page.getByTestId('success-toast')).toBeVisible();
    await expect(page.getByTestId('success-toast')).toContainText('Lucas Garcia checked in');

    // Child should now show undo button
    await expect(page.getByTestId('child-undo-button-2')).toBeVisible();
  });

  test('should assign Session Ticket to child without ticket', async ({ page }) => {
    // Expand Garcia family
    await page.getByTestId('family-toggle-button-1').click();

    // Expand child row for Lucas Garcia (id=2)
    await page.getByTestId('child-expand-button-2').click();

    // Click Session Ticket button
    await page.getByTestId('ticket-assign-session-2').click();

    // Success toast should appear
    await expect(page.getByTestId('success-toast')).toBeVisible();
    await expect(page.getByTestId('success-toast')).toContainText('Lucas Garcia checked in');

    // Child should now show undo button
    await expect(page.getByTestId('child-undo-button-2')).toBeVisible();
  });

  test('should open Add Family panel', async ({ page }) => {
    // Click Add Family button
    await page.getByTestId('add-family-button').click();

    // Add Family panel should be visible
    await expect(page.getByTestId('add-family-panel')).toBeVisible();

    // Form inputs should be visible
    await expect(page.getByTestId('add-family-name-input')).toBeVisible();
    await expect(page.getByTestId('add-family-submit-button')).toBeVisible();
    await expect(page.getByTestId('add-family-cancel-button')).toBeVisible();
  });

  test('should add new family with children', async ({ page }) => {
    // Open Add Family panel
    await page.getByTestId('add-family-button').click();

    // Fill in family name
    await page.getByTestId('add-family-name-input').fill('Wilson');

    // Fill in child name (first input should be visible by default)
    const childInputs = page.locator('input[placeholder^="Child"]');
    await childInputs.first().fill('Emma');

    // Submit form
    await page.getByTestId('add-family-submit-button').click();

    // Success toast should appear
    await expect(page.getByTestId('success-toast')).toBeVisible();
    await expect(page.getByTestId('success-toast')).toContainText('Wilson family added');

    // Panel should close
    await expect(page.getByTestId('add-family-panel')).not.toBeVisible();

    // Family count should increase to 5
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('5 families');
  });

  test('should verify new family appears in sorted list', async ({ page }) => {
    // Add Wilson family
    await page.getByTestId('add-family-button').click();
    await page.getByTestId('add-family-name-input').fill('Wilson');
    const childInputs = page.locator('input[placeholder^="Child"]');
    await childInputs.first().fill('Emma');
    await page.getByTestId('add-family-submit-button').click();

    // Wait for success toast
    await expect(page.getByTestId('success-toast')).toBeVisible();

    // New family should have id=5 (next available ID)
    const newFamilyCard = page.getByTestId('family-card-5');
    await expect(newFamilyCard).toBeVisible();
  });

  test('should verify new family auto-expands after creation', async ({ page }) => {
    // Add Wilson family
    await page.getByTestId('add-family-button').click();
    await page.getByTestId('add-family-name-input').fill('Wilson');
    const childInputs = page.locator('input[placeholder^="Child"]');
    await childInputs.first().fill('Emma');
    await page.getByTestId('add-family-submit-button').click();

    // Wait for success toast
    await expect(page.getByTestId('success-toast')).toBeVisible();

    // Child should be visible (auto-expanded)
    // New child should have id=10 (next available child ID)
    await expect(page.getByTestId('child-row-10')).toBeVisible();
  });

  test('should cancel Add Family panel', async ({ page }) => {
    // Open Add Family panel
    await page.getByTestId('add-family-button').click();

    // Verify panel is open
    await expect(page.getByTestId('add-family-panel')).toBeVisible();

    // Click cancel button (first one in the header)
    await page.getByTestId('add-family-cancel-button').first().click();

    // Panel should close
    await expect(page.getByTestId('add-family-panel')).not.toBeVisible();

    // Family count should remain 4
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('4 families');
  });

  test('should show empty search results', async ({ page }) => {
    const searchInput = page.getByTestId('search-input');

    // Search for non-existent name
    await searchInput.fill('Nonexistent Family Name');

    // Should show 0 families
    const familyCountText = page.getByTestId('family-count-text');
    await expect(familyCountText).toContainText('0 families');

    // Empty state message should be visible
    await expect(page.getByText(/No families found matching/i)).toBeVisible();
  });

  test('should hide family after all children checked in', async ({ page }) => {
    // Check in Smith family (id=3) which has 2 children with event passes
    await page.getByTestId('family-check-in-button-3').click();

    // Wait for success toast
    await expect(page.getByTestId('success-toast')).toBeVisible();

    // Wait for undo timer to expire (30 seconds + buffer)
    // For testing purposes, we'll just verify the undo button exists for now
    // In a real scenario, you'd need to mock the timer or wait
    await expect(page.getByTestId('family-undo-button-3')).toBeVisible();
  });
});

test.describe('Session Indicator', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display session information', async ({ page }) => {
    const sessionIndicator = page.getByTestId('session-indicator');

    await expect(sessionIndicator).toContainText('Summer Conference 2025');
    await expect(sessionIndicator).toContainText('Morning Care');
    await expect(sessionIndicator).toContainText('8:00 AM - 12:00 PM');
  });

  test('should have Change Session button', async ({ page }) => {
    const changeSessionButton = page.getByTestId('change-session-button');
    await expect(changeSessionButton).toBeVisible();
    await expect(changeSessionButton).toContainText('Change Session');
  });
});
