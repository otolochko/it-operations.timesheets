import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { AuthorFilter } from './AuthorFilter';

const authors = [
  { accountId: 'acc-1', displayName: 'Alice' },
  { accountId: 'acc-2', displayName: 'Bob' },
];

describe('AuthorFilter', () => {
  it('shows the selected/total count on the toggle button', () => {
    render(
      <AuthorFilter authors={authors} selected={new Set(['acc-1'])} onChange={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: 'Authors (1/2)' })).toBeInTheDocument();
  });

  it('opens the panel and filters the author list by search text', () => {
    render(<AuthorFilter authors={authors} selected={new Set()} onChange={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Authors/ }));
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search authors...'), {
      target: { value: 'ali' },
    });
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.queryByText('Bob')).not.toBeInTheDocument();
  });

  it('toggles an author checkbox and calls onChange with the updated set', () => {
    const onChange = vi.fn();
    render(<AuthorFilter authors={authors} selected={new Set(['acc-1'])} onChange={onChange} />);

    fireEvent.click(screen.getByRole('button', { name: /Authors/ }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Bob' }));

    expect(onChange).toHaveBeenCalledWith(new Set(['acc-1', 'acc-2']));
  });

  it('"Select all" and "Clear" update the selection', () => {
    const onChange = vi.fn();
    render(<AuthorFilter authors={authors} selected={new Set()} onChange={onChange} />);

    fireEvent.click(screen.getByRole('button', { name: /Authors/ }));
    fireEvent.click(screen.getByText('Select all'));
    expect(onChange).toHaveBeenCalledWith(new Set(['acc-1', 'acc-2']));

    fireEvent.click(screen.getByText('Clear'));
    expect(onChange).toHaveBeenCalledWith(new Set());
  });
});
