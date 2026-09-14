import * as React from 'react';
import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ThemeToggle } from '@/components/ThemeToggle';
import { ThemeProvider } from '@/lib/ThemeContext';
import { THEME_STORAGE_KEY } from '@/lib/theme/constants';

describe('ThemeToggle', () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    document.documentElement.style.colorScheme = '';
  });

  it('switches themes and persists the selection', async () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    const toggle = await screen.findByRole('button', { name: 'Switch to dark theme' });
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    });
    expect(document.documentElement.style.colorScheme).toBe('dark');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');
    expect(toggle).toHaveAccessibleName('Switch to light theme');
  });

  it('uses the theme initialized before hydration', async () => {
    document.documentElement.dataset.theme = 'dark';

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    expect(
      await screen.findByRole('button', { name: 'Switch to light theme' }),
    ).toBeInTheDocument();
  });
});
