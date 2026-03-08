# Frontend Test Plan - Theme Consistency & Component Functionality

## Overview

This test plan covers the recently updated components to ensure theme consistency and proper functionality across light/dark modes.

## Test Environment

- **Test Framework**: Vitest
- **Testing Library**: @testing-library/react
- **Commands**:
  - `npm run test` - Run tests
  - `npm run test:run` - Run tests in watch mode
  - `npm run test:coverage` - Run with coverage report

## Components to Test

### 1. GeneCapsuleExplore Page ✅ TESTED
**File**: `src/pages/GeneCapsuleExplore.tsx`
**Test File**: `src/pages/GeneCapsuleExplore.test.tsx`
**Status**: 18 tests passed

#### Theme Tests
- [x] Renders correctly in light mode
- [x] Renders correctly in dark mode
- [x] All text colors use theme-aware classes
- [x] Background colors adapt to theme
- [x] Border colors adapt to theme
- [x] Button styles adapt to theme

#### Functionality Tests
- [x] Search input works correctly
- [x] Skill filter adds/removes skills
- [x] Enter key triggers search
- [x] View mode toggle (grid/list) works
- [x] Sort by dropdown works
- [x] Sort order toggle works
- [x] Loading state displays correctly
- [x] Error state displays correctly
- [x] Empty state displays correctly
- [x] No results state displays correctly
- [x] Agent cards navigate to detail page on click

### 2. APIKeyManager Component
**File**: `src/components/APIKeyManager.tsx`

#### Theme Tests
- [ ] Renders correctly in light mode
- [ ] Renders correctly in dark mode
- [ ] Error messages use theme-aware colors
- [ ] Key cards use theme-aware styles
- [ ] Modal uses theme-aware styles

#### Functionality Tests
- [ ] Loads API keys on mount
- [ ] Shows loading state
- [ ] Shows empty state when no keys
- [ ] Create key modal opens/closes
- [ ] Create key form validation works
- [ ] Key creation success flow works
- [ ] Copy to clipboard works
- [ ] Revoke key confirmation works
- [ ] Renew key works
- [ ] Error handling displays correctly
- [ ] Expiry status shows correct colors

### 3. GeneCapsuleDisplay Component
**File**: `src/components/GeneCapsuleDisplay.tsx`

#### Theme Tests
- [ ] Renders correctly in light mode
- [ ] Renders correctly in dark mode
- [ ] Tab styles adapt to theme
- [ ] Card backgrounds adapt to theme
- [ ] Empty states use theme-aware styles

#### Functionality Tests
- [ ] Loads gene capsule on mount
- [ ] Shows loading state
- [ ] Shows error state
- [ ] Tab switching works (experiences/skills/patterns)
- [ ] Summary stats display correctly
- [ ] Experience cards render correctly
- [ ] Skill cards render correctly
- [ ] Pattern cards render correctly
- [ ] Empty state shows when no data
- [ ] Visibility toggle works
- [ ] Search panel toggles correctly

### 4. StakingPanel Component
**File**: `src/components/StakingPanel.tsx`

#### Theme Tests
- [ ] Renders correctly in light mode
- [ ] Renders correctly in dark mode
- [ ] Tier colors display correctly
- [ ] Progress bars use theme-aware styles
- [ ] Buttons use theme-aware styles

#### Functionality Tests
- [ ] Loads staking info on mount
- [ ] Shows loading state
- [ ] Displays staked amount correctly
- [ ] Displays pending rewards correctly
- [ ] Tier progress shows correctly
- [ ] Tier benefits display correctly
- [ ] All tiers display correctly
- [ ] Current tier indicator works
- [ ] Deposit modal opens/closes
- [ ] Deposit form validation works
- [ ] Deposit submission works
- [ ] Withdraw modal opens/closes
- [ ] Withdraw form validation works
- [ ] Withdraw submission works
- [ ] Claim rewards button works
- [ ] Error handling displays correctly

## Debug Checklist

### Before Testing
- [ ] Backend server is running on port 8000
- [ ] Frontend dev server is running on port 5173
- [ ] Database has test data (agents, gene capsules, API keys)

### Manual Testing Steps

#### 1. GeneCapsuleExplore Page
```
1. Navigate to /app/gene-capsule/explore
2. Toggle theme (light/dark) - verify all elements adapt
3. Enter search query and press Enter
4. Add skill filters
5. Toggle between grid/list view
6. Change sort options
7. Click on an agent card
```

#### 2. APIKeyManager (in Agent Detail)
```
1. Navigate to /app/agents/{agent_id}
2. Click on "API Keys" tab
3. Toggle theme - verify styles adapt
4. Click "Create Key"
5. Fill form and submit
6. Copy the generated key
7. Test renew and revoke buttons
```

#### 3. GeneCapsuleDisplay (in Agent Detail)
```
1. Navigate to /app/agents/{agent_id}
2. Click on "Gene Capsule" tab
3. Toggle theme - verify styles adapt
4. Switch between Experiences/Skills/Patterns tabs
5. Test visibility toggle on experiences
6. Verify empty states if no data
```

#### 4. StakingPanel (in Agent Detail)
```
1. Navigate to /app/agents/{agent_id}
2. Click on "Staking" tab
3. Toggle theme - verify styles adapt
4. Verify tier display
5. Test deposit modal
6. Test withdraw modal
7. Test claim rewards
```

## Test Data Requirements

### Agents
- At least 2-3 registered agents with different statuses
- One agent with wallet binding
- One agent without wallet binding

### Gene Capsules
- At least one agent with gene capsule data
- At least one agent without gene capsule data (for empty state testing)

### API Keys
- At least one agent with existing API keys
- At least one agent without API keys (for empty state testing)

### Staking
- User with staked tokens
- User with no staked tokens

## Running Tests

```bash
# Run all tests
npm run test

# Run specific test file
npm run test -- GeneCapsuleExplore.test.tsx

# Run with coverage
npm run test:coverage

# Run in watch mode during development
npm run test:run
```

## Expected Coverage Goals

- **Statements**: > 80%
- **Branches**: > 75%
- **Functions**: > 80%
- **Lines**: > 80%

## Notes

1. All components should be tested with both light and dark themes
2. Mock API calls for isolated component testing
3. Use `@testing-library/user-event` for user interactions
4. Test accessibility (keyboard navigation, screen reader support)

---

## Test Execution Summary

**Date**: 2026-03-08
**Total Tests**: 51 passed
**Duration**: ~1.8s

| Component | Tests | Status |
|-----------|-------|--------|
| GeneCapsuleExplore | 18 | ✅ All passed |
| Button | 6 | ✅ All passed |
| API | 7 | ✅ All passed |
| statusColors | 20 | ✅ All passed |

### Verified Theme Patterns in GeneCapsuleExplore:
- ✅ `text-light-text-primary dark:text-secondary-100` for primary text
- ✅ `text-secondary-500 dark:text-secondary-400` for secondary text
- ✅ `card` class for containers
- ✅ `btn btn-primary` and `btn btn-secondary` for buttons
- ✅ `bg-white dark:bg-gray-800` for inputs
- ✅ `bg-red-50 dark:bg-red-900/20` for error states
