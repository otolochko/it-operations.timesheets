import * as React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { LogViewer } from '@/components/LogViewer';

describe('LogViewer', () => {
  it('scrolls to the latest line when the log changes', () => {
    const { rerender } = render(<LogViewer logText="Sync started" />);
    const viewer = screen.getByRole('region', { name: 'Sync log' });

    Object.defineProperty(viewer, 'scrollHeight', {
      configurable: true,
      value: 480,
    });
    viewer.scrollTop = 0;

    rerender(<LogViewer logText={'Sync started\nFetched 100 worklogs'} />);

    expect(viewer.scrollTop).toBe(480);
  });
});
