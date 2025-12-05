# Testing Guide - Conference Child Management System Frontend

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project uses **Vitest** and **Testing Library** for component testing. Tests are written in TypeScript and run in a jsdom environment.

### Why Component Tests?

**Speed**: Component tests run in 2-3 seconds (vs 15-20 seconds for E2E tests)
**Focus**: Test individual component behavior in isolation
**Confidence**: Catch bugs before they reach integration testing
**Developer Experience**: Fast feedback loop during development

### Testing Philosophy

> "The more your tests resemble the way your software is used, the more confidence they can give you."
> — Kent C. Dodds

We test **user behavior**, not implementation details:
- ✅ What users **see** (text, labels, buttons)
- ✅ What users **do** (click, type, submit)
- ✅ What users **experience** (success/error messages)
- ❌ Component internals ($state, function names)
- ❌ CSS classes (unless for accessibility)

---

## Quick Start

### Install Dependencies
```bash
cd frontend
pnpm install
```

### Run Tests
```bash
# Run tests in watch mode (recommended for development)
pnpm test

# Run tests once
pnpm test run

# Run tests with interactive UI
pnpm test:ui

# Run tests with coverage report
pnpm test:coverage
```

### Create Your First Test
```typescript
// src/lib/components/MyComponent.test.ts
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import MyComponent from './MyComponent.svelte';

describe('MyComponent', () => {
  it('renders greeting message', () => {
    render(MyComponent, { props: { name: 'World' } });

    expect(screen.getByText('Hello, World!')).toBeInTheDocument();
  });

  it('handles button click', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(MyComponent, { props: { onClick } });

    await user.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalled();
  });
});
```

---

## Test Structure

### File Organization
```
frontend/src/
├── lib/
│   ├── components/
│   │   ├── MyComponent.svelte
│   │   ├── MyComponent.test.ts          # Component tests
│   │   ├── __tests__/                   # Alternative: tests folder
│   │   │   └── ComplexComponent.test.ts
│   │   └── domain/
│   │       ├── FamilyTable.svelte
│   │       └── FamilyTable.test.ts
│   ├── __mocks__/                       # Mock implementations
│   │   └── $app/
│   │       ├── navigation.ts
│   │       └── stores.ts
│   └── test-utils.ts                    # Shared test utilities
├── routes/
│   └── login/
│       └── +page.svelte                 # Don't test here (+ files reserved)
└── setupTests.ts                        # Global test setup
```

### Naming Conventions
- Test files: `ComponentName.test.ts` or `ComponentName.spec.ts`
- Test suites: `describe('ComponentName', () => { ... })`
- Test cases: `it('should do something', () => { ... })`

---

## Writing Tests

### 1. Basic Component Rendering

```typescript
import { render, screen } from '@testing-library/svelte';
import Button from './Button.svelte';

it('renders button with label', () => {
  render(Button, { props: { label: 'Click me' } });

  expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
});
```

### 2. User Interactions

```typescript
import userEvent from '@testing-library/user-event';

it('handles button click', async () => {
  const user = userEvent.setup();
  const onClick = vi.fn();

  render(Button, { props: { onClick } });

  await user.click(screen.getByRole('button'));

  expect(onClick).toHaveBeenCalled();
});
```

### 3. Form Interactions

```typescript
it('submits form with user input', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();

  render(LoginForm, { props: { onSubmit } });

  // Type into inputs
  await user.type(screen.getByLabelText('Username'), 'testuser');
  await user.type(screen.getByLabelText('Password'), 'password123');

  // Submit form
  await user.click(screen.getByRole('button', { name: 'Login' }));

  expect(onSubmit).toHaveBeenCalledWith({
    username: 'testuser',
    password: 'password123'
  });
});
```

### 4. Testing Async Behavior

```typescript
import { waitFor } from '@testing-library/svelte';

it('shows loading state then success message', async () => {
  const user = userEvent.setup();
  render(AsyncComponent);

  await user.click(screen.getByRole('button', { name: 'Load Data' }));

  // Check loading state
  expect(screen.getByText('Loading...')).toBeInTheDocument();

  // Wait for success message
  await waitFor(() => {
    expect(screen.getByText('Success!')).toBeInTheDocument();
  });
});
```

### 5. Mocking API Calls

```typescript
import { vi } from 'vitest';

vi.mock('$lib/api/client', () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ success: true })
  }
}));

it('calls API on form submit', async () => {
  const { apiClient } = await import('$lib/api/client');
  const user = userEvent.setup();

  render(LoginPage);

  await user.type(screen.getByLabelText('Username'), 'testuser');
  await user.type(screen.getByLabelText('Password'), 'password123');
  await user.click(screen.getByRole('button', { name: 'Login' }));

  expect(apiClient.post).toHaveBeenCalledWith('/auth/login/', {
    username: 'testuser',
    password: 'password123'
  });
});
```

### 6. Testing i18n

```typescript
vi.mock('svelte-i18n', () => ({
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => {
        const translations: Record<string, string> = {
          'login.title': 'Login',
          'login.username': 'Username'
        };
        return translations[key] || key;
      });
      return () => {};
    })
  }
}));

it('renders translated text', () => {
  render(LoginPage);

  expect(screen.getByText('Login')).toBeInTheDocument();
  expect(screen.getByLabelText('Username')).toBeInTheDocument();
});
```

### 7. Testing Conditional Rendering

```typescript
it('shows error message when error prop is provided', () => {
  render(Alert, { props: { error: 'Something went wrong' } });

  expect(screen.getByText('Something went wrong')).toBeInTheDocument();
});

it('hides error message when no error', () => {
  render(Alert, { props: { error: null } });

  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
```

### 8. Testing Accessibility

```typescript
it('has accessible form labels', () => {
  render(LoginForm);

  const usernameInput = screen.getByLabelText('Username');
  const passwordInput = screen.getByLabelText('Password');

  expect(usernameInput).toHaveAttribute('required');
  expect(passwordInput).toHaveAttribute('type', 'password');
});

it('has proper ARIA attributes', () => {
  render(Modal, { props: { isOpen: true } });

  const dialog = screen.getByRole('dialog');
  expect(dialog).toHaveAttribute('aria-labelledby');
});
```

---

## Running Tests

### Development Workflow

```bash
# Watch mode - tests re-run on file changes
pnpm test

# Run specific test file
pnpm test LoginPage.test.ts

# Run tests matching pattern
pnpm test -- -t "renders login form"

# Run tests in specific folder
pnpm test components/domain
```

### CI/CD

```bash
# Run all tests once (non-interactive)
pnpm test run

# Run with coverage
pnpm test:coverage

# Exit with error code if tests fail
pnpm test run --reporter=verbose
```

### Interactive UI

```bash
# Open Vitest UI in browser
pnpm test:ui
```

Features:
- Visual test results
- Component tree view
- Time travel debugging
- Filter tests by status
- Re-run failed tests

### Coverage Reports

```bash
pnpm test:coverage
```

Generates:
- Terminal summary
- HTML report in `coverage/index.html`

Coverage thresholds (recommended):
- **Statements**: 80%
- **Branches**: 75%
- **Functions**: 80%
- **Lines**: 80%

---

## Best Practices

### ✅ DO

**1. Use semantic queries (in order of preference)**
```typescript
// Best - Accessible to everyone
screen.getByRole('button', { name: 'Submit' })
screen.getByLabelText('Username')
screen.getByPlaceholderText('Enter email')
screen.getByText('Welcome')

// Good - Useful for non-interactive elements
screen.getByDisplayValue('Current value')
screen.getByAltText('Profile picture')
screen.getByTitle('Close')

// Last resort - Use data-testid only when necessary
screen.getByTestId('custom-element')
```

**2. Test user-facing behavior**
```typescript
// ✅ Good - Tests what user sees
expect(screen.getByText('Item added to cart')).toBeInTheDocument();

// ❌ Bad - Tests implementation
expect(component.cartItems.length).toBe(1);
```

**3. Use userEvent for interactions**
```typescript
// ✅ Good - Simulates real user interaction
const user = userEvent.setup();
await user.click(button);
await user.type(input, 'text');

// ❌ Avoid - Doesn't simulate real events
button.click();
input.value = 'text';
```

**4. Test one thing per test**
```typescript
// ✅ Good
it('shows error message on invalid email', () => { ... });
it('clears error when email becomes valid', () => { ... });

// ❌ Bad - Tests multiple behaviors
it('handles email validation', () => {
  // Tests error, success, clearing, etc.
});
```

**5. Use descriptive test names**
```typescript
// ✅ Good
it('disables submit button while form is submitting')
it('shows validation error when email is invalid')

// ❌ Bad
it('works correctly')
it('test button')
```

### ❌ DON'T

**1. Don't test implementation details**
```typescript
// ❌ Bad - Tests internal state
expect(component.isLoading).toBe(true);
expect(component.handleClick).toHaveBeenCalled();

// ✅ Good - Tests visible behavior
expect(screen.getByText('Loading...')).toBeInTheDocument();
expect(screen.getByRole('button')).toBeDisabled();
```

**2. Don't use brittle selectors**
```typescript
// ❌ Bad - Breaks when CSS changes
container.querySelector('.btn-primary');
container.querySelector('#submit-button');

// ✅ Good - Semantic, accessible queries
screen.getByRole('button', { name: 'Submit' });
```

**3. Don't test third-party libraries**
```typescript
// ❌ Bad - Tests svelte-i18n library
expect(locale.set).toHaveBeenCalled();

// ✅ Good - Tests that your component uses the library correctly
expect(screen.getByText('Translated Text')).toBeInTheDocument();
```

**4. Don't use random test data**
```typescript
// ❌ Bad - Non-deterministic
const randomId = Math.random();

// ✅ Good - Predictable test data
const testId = 'test-user-123';
```

**5. Don't have long setup in tests**
```typescript
// ❌ Bad - Setup duplicated across tests
it('test 1', () => {
  const user = createUser();
  const session = createSession();
  // ... lots of setup
});

// ✅ Good - Extract to helper or beforeEach
function renderLoginForm() {
  return render(LoginForm, { props: { /* defaults */ } });
}
```

---

## Common Patterns

### Pattern 1: Render Helper

Create a custom render function with common providers:

```typescript
// src/lib/test-utils.ts
import { render } from '@testing-library/svelte';

export function renderWithI18n(component, options = {}) {
  return render(component, {
    ...options,
    // Add common wrappers/providers here
  });
}

// Usage in tests
import { renderWithI18n } from '$lib/test-utils';

it('renders with translations', () => {
  renderWithI18n(MyComponent);
  expect(screen.getByText('Translated')).toBeInTheDocument();
});
```

### Pattern 2: Test Fixtures

Create reusable test data:

```typescript
// src/lib/test-fixtures.ts
export const mockFamily = {
  id: 'family-1',
  name: 'Smith',
  children: [
    {
      id: 'child-1',
      firstName: 'Emma',
      lastName: 'Smith',
      birthdate: '2020-01-01'
    }
  ]
};

export const mockSession = {
  id: 'session-1',
  name: 'Morning Childcare',
  startTime: '2025-12-03T09:00:00Z',
  endTime: '2025-12-03T12:00:00Z',
  isActive: true
};

// Usage
import { mockFamily } from '$lib/test-fixtures';

it('displays family name', () => {
  render(FamilyCard, { props: { family: mockFamily } });
  expect(screen.getByText('Smith')).toBeInTheDocument();
});
```

### Pattern 3: Mock Factory Functions

Create functions that generate mocks with defaults:

```typescript
// src/lib/test-utils.ts
export function createMockChild(overrides = {}) {
  return {
    id: 'child-1',
    firstName: 'Test',
    lastName: 'Child',
    birthdate: '2020-01-01',
    ...overrides
  };
}

// Usage
it('handles child with allergies', () => {
  const child = createMockChild({ allergies: 'Peanuts' });
  render(ChildCard, { props: { child } });
  expect(screen.getByText('Allergies: Peanuts')).toBeInTheDocument();
});
```

### Pattern 4: Custom Matchers

Extend expect with custom assertions:

```typescript
// src/setupTests.ts
import { expect } from 'vitest';

expect.extend({
  toBeVisible(element) {
    const isVisible = element.offsetParent !== null;
    return {
      pass: isVisible,
      message: () => `Expected element to ${isVisible ? 'not ' : ''}be visible`
    };
  }
});

// Usage
expect(screen.getByTestId('modal')).toBeVisible();
```

### Pattern 5: Testing Hooks

For testing SvelteKit navigation, stores, etc.:

```typescript
// src/__mocks__/$app/navigation.ts
import { vi } from 'vitest';

export const goto = vi.fn();
export const invalidate = vi.fn();

// In test
import { goto } from '$app/navigation';

it('navigates on success', async () => {
  render(LoginPage);
  // ... trigger navigation
  expect(goto).toHaveBeenCalledWith('/dashboard');
});
```

---

## Troubleshooting

### Issue: Tests fail with "mount(...) is not available on the server"

**Cause**: Using wrong Vite config (SvelteKit SSR mode)

**Solution**: Ensure tests use `vitest.config.ts`:
```bash
pnpm test --config vitest.config.ts
```

Check `package.json`:
```json
{
  "scripts": {
    "test": "vitest --config vitest.config.ts"
  }
}
```

---

### Issue: Cannot find $lib or $app imports

**Cause**: Missing path aliases in test config

**Solution**: Check `vitest.config.ts`:
```typescript
export default defineConfig({
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib'),
      $app: path.resolve('./src/__mocks__/$app')
    }
  }
});
```

---

### Issue: Tests timeout on user interactions

**Cause**: Not awaiting async operations

**Solution**: Always await userEvent methods:
```typescript
// ❌ Bad
user.click(button);

// ✅ Good
await user.click(button);
```

---

### Issue: "TestingLibraryElementError: Unable to find element"

**Cause**: Element not rendered or query is incorrect

**Solution**: Debug with screen.debug():
```typescript
it('finds element', () => {
  render(MyComponent);

  screen.debug(); // Print entire DOM
  screen.debug(screen.getByRole('button')); // Print specific element

  expect(screen.getByRole('button')).toBeInTheDocument();
});
```

Use `*ByRole` with logTestingPlaygroundURL:
```typescript
screen.logTestingPlaygroundURL(); // Opens interactive query builder
```

---

### Issue: Flaky tests (sometimes pass, sometimes fail)

**Common causes**:
1. **Race conditions** - Not waiting for async updates
2. **Shared state** - Tests affecting each other
3. **Random data** - Using Math.random() or Date.now()

**Solutions**:
```typescript
// Wait for async updates
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});

// Clear mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});

// Use deterministic data
const FIXED_DATE = new Date('2025-12-03T10:00:00Z');
vi.setSystemTime(FIXED_DATE);
```

---

### Issue: Mock not being called

**Cause**: Mock defined after import

**Solution**: Use vi.mock() at top level:
```typescript
// ✅ Good - Mock before imports
vi.mock('$lib/api/client');

import { apiClient } from '$lib/api/client';

// ❌ Bad - Import before mock
import { apiClient } from '$lib/api/client';
vi.mock('$lib/api/client'); // Too late!
```

---

### Issue: Component props not updating

**Cause**: Svelte 5 removed `$set()` API

**Solution**: Re-render component or test callback pattern:
```typescript
// ❌ Bad - $set() removed in Svelte 5
component.$set({ value: 'new' });

// ✅ Good - Test through callbacks
let value = 'initial';
render(MyComponent, {
  props: {
    value,
    onChange: (newValue) => { value = newValue; }
  }
});

// Trigger change
await user.type(input, 'new');
expect(value).toBe('new');
```

---

## Additional Resources

### Official Documentation
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Svelte](https://testing-library.com/docs/svelte-testing-library/intro)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [Svelte 5 Testing Guide](https://svelte.dev/docs/svelte/testing)

### Community Resources
- [Common Mistakes with Testing Library](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [Testing Library Playground](https://testing-playground.com/)

### Internal Documentation
- [UI_TESTING.md](./UI_TESTING.md) - Testing strategy and architecture
- [TESTING_SUMMARY.md](../TESTING_SUMMARY.md) - Implementation summary

---

## Contributing

### Adding New Tests

1. Create test file next to component: `ComponentName.test.ts`
2. Follow naming conventions and structure
3. Test user-facing behavior, not implementation
4. Ensure tests are focused and descriptive
5. Run tests locally before committing

### Test Coverage Goals

- **New components**: 80%+ coverage
- **Critical flows**: 90%+ coverage (login, check-in, checkout)
- **Utility functions**: 100% coverage

### Code Review Checklist

- [ ] Tests follow Testing Library best practices
- [ ] Tests use semantic queries (getByRole, getByLabelText)
- [ ] Tests are focused (one behavior per test)
- [ ] Tests have descriptive names
- [ ] Async operations are properly awaited
- [ ] Mocks are cleared between tests
- [ ] No implementation details are tested
- [ ] All tests pass locally

---

## FAQ

**Q: Should I test internal state?**
A: No. Test what users see and interact with, not component internals.

**Q: When should I use getByTestId?**
A: Only as a last resort when semantic queries aren't possible.

**Q: Should I test third-party libraries?**
A: No. Assume they work. Test that YOUR code uses them correctly.

**Q: How do I test SvelteKit-specific features?**
A: Mock them in `src/__mocks__/$app/` and test your component's behavior.

**Q: Should every component have tests?**
A: Prioritize: critical flows > complex logic > simple components.

**Q: Do component tests replace E2E tests?**
A: No. They're complementary. Use both for maximum confidence.

---

**Last Updated**: 2025-12-03
**Maintained By**: Development Team
