/**
 * setup.js  –  Vitest global test setup
 *
 * Runs before every test file. Extends expect with jest-dom matchers
 * and resets mocks after each test.
 */
import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Auto-cleanup React trees after every test
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
