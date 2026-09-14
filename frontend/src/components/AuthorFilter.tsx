'use client';

import * as React from 'react';
import { SecondaryButton } from './Buttons';

export interface AuthorOption {
  accountId: string;
  displayName: string;
}

export interface AuthorFilterProps {
  authors: AuthorOption[];
  selected: Set<string>;
  onChange: (selected: Set<string>) => void;
}

export function AuthorFilter({ authors, selected, onChange }: AuthorFilterProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const filteredAuthors = authors.filter((author) =>
    author.displayName.toLowerCase().includes(search.toLowerCase()),
  );

  function toggle(accountId: string) {
    const next = new Set(selected);
    if (next.has(accountId)) {
      next.delete(accountId);
    } else {
      next.add(accountId);
    }
    onChange(next);
  }

  return (
    <div ref={containerRef} className="relative">
      <SecondaryButton type="button" onClick={() => setOpen((prev) => !prev)}>
        Authors ({selected.size}/{authors.length})
      </SecondaryButton>
      {open ? (
        <div className="absolute z-10 mt-2 w-64 rounded-lg border border-border bg-card p-3 shadow-lg">
          <input
            type="text"
            placeholder="Search authors..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="mb-2 w-full rounded-md border border-border bg-field-bg px-3 py-1.5 text-sm text-text-primary"
          />
          <div className="mb-2 flex gap-2">
            <button
              type="button"
              onClick={() => onChange(new Set(authors.map((author) => author.accountId)))}
              className="text-xs text-accent hover:underline"
            >
              Select all
            </button>
            <button
              type="button"
              onClick={() => onChange(new Set())}
              className="text-xs text-accent hover:underline"
            >
              Clear
            </button>
          </div>
          <div className="max-h-56 overflow-y-auto">
            {filteredAuthors.length === 0 ? (
              <p className="text-sm text-text-muted">No authors found.</p>
            ) : (
              filteredAuthors.map((author) => (
                <label
                  key={author.accountId}
                  className="flex items-center gap-2 rounded px-1 py-1 text-sm text-text-primary hover:bg-surface-raised"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(author.accountId)}
                    onChange={() => toggle(author.accountId)}
                  />
                  {author.displayName}
                </label>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
