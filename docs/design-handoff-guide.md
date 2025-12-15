# Design Handoff Guide: React to Svelte Translation

## Purpose
This guide explains the optimal format for providing a React design implementation that will be translated to Svelte for the checkout page.

## What I Need (In Order of Preference)

### Option 1: Pure HTML + Tailwind CSS (BEST)
**Why**: Zero ambiguity, no framework translation needed, can copy-paste directly.

**Format**:
```html
<!-- Example structure -->
<div class="bg-white border border-slate-300 rounded-lg p-4 mb-3">
  <div class="flex items-center justify-between mb-2">
    <h3 class="font-bold text-lg text-blue-900">Smith Family (2)</h3>
    <button class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
      Check Out All
    </button>
  </div>

  <!-- Child row -->
  <div class="flex items-center justify-between py-2 border-t border-slate-200">
    <div>
      <span class="text-slate-700">Emma Smith</span>
      <span class="text-xs text-slate-500 ml-2">15:30</span>
    </div>
    <button class="px-3 py-1 bg-red-500 text-white text-sm rounded">
      Check Out
    </button>
  </div>
</div>
```

**What to include**:
- Complete HTML structure for one family card/row
- All Tailwind classes exactly as they should appear
- Responsive breakpoints (sm:, md:, lg:) if design changes by screen size
- Comments for interactive states (`:hover`, `:focus`, `:disabled`) if not using Tailwind's built-in variants
- A second example if there are different states (e.g., family with 1 child vs 3 children)

**What NOT to include**:
- JavaScript/React code
- Event handlers (onClick, etc.)
- State management
- Data mapping/loops
- API calls

### Option 2: React Component + Static HTML Output
**Why**: I can see the structure and copy the rendered HTML.

**Format**:
1. Provide the React JSX component
2. Provide the **rendered HTML output** (inspect element and copy the actual DOM)
3. Note any dynamic class changes (e.g., "add bg-slate-100 when even row")

**Example**:
```jsx
// FamilyCard.jsx
function FamilyCard({ family }) {
  return (
    <div className="bg-white rounded-lg p-4">
      <h3 className="font-bold text-lg">{family.name} ({family.children.length})</h3>
      {/* ... */}
    </div>
  );
}

// RENDERED HTML (from browser inspector):
<div class="bg-white rounded-lg p-4">
  <h3 class="font-bold text-lg">Smith Family (2)</h3>
  <!-- ... -->
</div>
```

### Option 3: React Component + Screenshots + Specifications
**Why**: Visual reference helps but requires more interpretation.

**What to provide**:
1. **Screenshots**:
   - Mobile view (375px width)
   - Desktop view (1280px width)
   - Different states (1 child, multiple children, hover states)
   - Annotate with measurements if critical (e.g., "24px gap between children")

2. **React component code** (I'll translate the structure)

3. **Design specifications** in text:
   ```markdown
   ## Layout
   - Each family is a card with 16px padding
   - 12px gap between cards
   - Border radius: 8px
   - Border: 1px solid slate-300

   ## Typography
   - Family name: font-bold, text-lg (18px), text-blue-900
   - Child name: text-base (16px), text-slate-700
   - Time: text-xs (12px), text-slate-500

   ## Spacing
   - Header: 8px bottom margin
   - Between children: 8px vertical padding, 1px border-top

   ## Responsive
   - Mobile (<640px): Stack buttons below child name
   - Desktop (≥640px): Buttons inline to the right

   ## Colors
   - Primary action (Check Out All): bg-red-600, hover:bg-red-700
   - Individual checkout: bg-red-500, hover:bg-red-600
   - Text: Slate scale (900 for headings, 700 for body, 500 for meta)
   ```

## What I'll Do With It

1. **Extract the structure**: Understand the DOM hierarchy
2. **Convert to Svelte syntax**:
   - `className` → `class`
   - `{variable}` → `{variable}` (same interpolation)
   - `map()` → `{#each}` blocks
   - Conditional rendering → `{#if}` blocks
3. **Wire up functionality**: Add event handlers, data binding
4. **Maintain existing patterns**: Use existing i18n keys, API calls, state management
5. **Test responsiveness**: Verify mobile and desktop layouts

## Critical Information to Include

### Must Have:
- [ ] Complete HTML structure for at least one example
- [ ] All Tailwind CSS classes used
- [ ] Responsive breakpoints if design changes by screen size
- [ ] Text content examples (so I know what's dynamic vs static)

### Very Helpful:
- [ ] Multiple examples showing edge cases (1 child, 5 children, etc.)
- [ ] Hover/focus states if they differ from default Tailwind
- [ ] Mobile screenshot + Desktop screenshot
- [ ] Notes on any animations or transitions

### Not Needed:
- ❌ JavaScript logic, state management, or React hooks
- ❌ Event handler implementations
- ❌ API integration code
- ❌ Prop types or TypeScript types
- ❌ Detailed component composition (I'll handle breaking it into components)

## Example: Perfect Handoff

```markdown
## Checkout Design - Compact Card Layout

### Desktop Layout (≥640px)
[Screenshot attached: checkout-desktop.png]

### Mobile Layout (<640px)
[Screenshot attached: checkout-mobile.png]

### HTML Structure (Single Family with 2 Children)

```html
<div class="bg-white border-l-4 border-blue-600 rounded-r shadow-sm mb-2 p-3">
  <!-- Family header -->
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-3">
      <h4 class="font-semibold text-slate-800 text-sm">Smith Family</h4>
      <span class="text-xs text-slate-500">(2 children)</span>
    </div>
    <button class="px-3 py-1.5 bg-red-600 text-white text-sm font-semibold rounded hover:bg-red-700 transition-colors">
      Check Out All
    </button>
  </div>

  <!-- Child 1 -->
  <div class="flex items-center justify-between py-1.5 border-t border-slate-100">
    <div class="flex-1">
      <span class="text-slate-700 text-sm">Emma Smith</span>
      <span class="text-slate-400 text-xs ml-2">15:30</span>
    </div>
    <button class="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600">
      Out
    </button>
  </div>

  <!-- Child 2 -->
  <div class="flex items-center justify-between py-1.5 border-t border-slate-100">
    <div class="flex-1">
      <span class="text-slate-700 text-sm">Oliver Smith</span>
      <span class="text-slate-400 text-xs ml-2">15:32</span>
    </div>
    <button class="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600">
      Out
    </button>
  </div>

  <!-- Pickup selector -->
  <div class="flex items-center gap-2 mt-2 pt-2 border-t border-slate-200">
    <label class="text-xs text-slate-600 whitespace-nowrap">Picked up by:</label>
    <select class="flex-1 text-xs px-2 py-1 border border-slate-300 rounded bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
      <option value="">Select person...</option>
      <option value="parent1">Sarah Smith (Parent)</option>
      <option value="parent2">John Smith (Parent)</option>
    </select>
  </div>
</div>
```

### Design Notes
- Left border color (blue-600) visually separates families
- Minimal vertical padding to reduce scrolling (user requirement)
- "Out" button abbreviated to save horizontal space on mobile
- Transitions on buttons: `transition-colors` for smooth hover
- Focus states: Use Tailwind's default `focus:ring-2 focus:ring-blue-500`

### Responsive Behavior
- No layout changes between mobile/desktop - same structure works for both
- If viewport < 375px, text might truncate with `truncate` class (not shown here)

### Dynamic Content Notes
- Family name: Replace "Smith Family" with `{family.display_name}`
- Child count: Replace "(2 children)" with count
- Child rows: Loop/repeat the child div structure
- Time: Format as HH:MM from ISO timestamp
- Select options: Generate from family.parents array
```

## Common Translation Patterns

When I see this in React → I'll translate to Svelte:

| React | Svelte 5 (Runes) |
|-------|------------------|
| `className="..."` | `class="..."` |
| `{items.map(item => ...)}` | `{#each items as item}...{/each}` |
| `{condition && <div>...</div>}` | `{#if condition}<div>...</div>{/if}` |
| `{condition ? 'a' : 'b'}` | `{condition ? 'a' : 'b'}` (same) |
| `onClick={handler}` | `on:click={handler}` or `onclick={handler}` |
| `onChange={handler}` | `on:change={handler}` or `onchange={handler}` |
| `value={state}` | `bind:value={state}` |
| `style={{...}}` | `style="..."` (inline string) |

## What Happens After Handoff

1. I'll create the Svelte component with your HTML structure
2. Wire up data binding and event handlers
3. Integrate with existing i18n (translation) system
4. Connect to existing API and state management
5. Test on mobile and desktop viewports
6. Show you the result with screenshots

## Questions I Might Ask

- "What should happen when [edge case]?"
- "Should [element] have a specific state when [condition]?"
- "Is this spacing intentional or can I adjust for consistency?"

## Red Flags (Things to Avoid)

❌ **Don't provide**:
- Custom CSS in `<style>` tags (use Tailwind classes only)
- JavaScript frameworks other than React (Vue, Angular, etc.)
- Inline styles unless absolutely necessary for dynamic values
- External CSS frameworks (Bootstrap, Material-UI, etc.)

✅ **Do provide**:
- Pure Tailwind utility classes
- Static HTML examples
- Clear visual references (screenshots)
- Notes on responsive behavior
- Examples of different states

## Summary: The Golden Path

**Best possible handoff**:
1. Clean HTML with Tailwind classes
2. Mobile + Desktop screenshots
3. Brief notes on any special interactions
4. Examples showing 1 child vs multiple children cases

This lets me focus on Svelte translation and integration without guessing design intent.
