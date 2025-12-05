# Feature 3: Auto-expand on Child Name Search

## Requirements
- When search term matches a child's first name (but NOT the family surname), auto-expand that family card
- Example: Searching "Emma" should auto-expand families containing a child named Emma, but only if "Emma" is not in the family surname
- Clearing search should keep families expanded (less disruptive)

## Implementation Approach

### Logic
1. Add useEffect that monitors `searchQuery` changes
2. For each visible family, check if search matches child name but not family name:
   - Extract search query in lowercase
   - Check if family name (surname) contains the search query
   - If family name does NOT contain search query, check each child's name
   - If any child's name contains the search query, add family.id to expandedFamilies Set
3. Only auto-expand when adding new search terms (not when clearing)

### Edge Cases
- Empty search: Do nothing (don't collapse families)
- Search matches both family name and child name: Do nothing (already visible by family name match)
- Search matches only child name: Auto-expand that family
- Multiple families match: Auto-expand all matching families

### Code Location
`/workspace/checkin-experiment/src/App.tsx` - Add useEffect after existing hooks

## Testing Strategy

Since this is an integration feature involving state management and multiple components:

### Manual Testing Checklist
1. Search for "Emma" - should auto-expand Anderson and Smith families (if they have Emma)
2. Search for "Garcia" - should NOT auto-expand Garcia family (matches family name)
3. Clear search - families should remain expanded
4. Search for non-existent name - no families should auto-expand
5. Search progressively (e.g., "E", "Em", "Emma") - should expand as match is found

### Automated Testing (Future)
Could add integration tests using @testing-library/react to:
- Render App component
- Simulate search input
- Assert on expanded state of family cards

## Implementation Date
December 4, 2025
