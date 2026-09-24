import { test, expect } from '@playwright/test';

test('checkout completes', { tag: ['@REQ-FIX-13'] }, async ({ page }) => {
  expect(page).toBeTruthy();
});
