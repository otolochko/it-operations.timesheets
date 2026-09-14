'use client';

import * as React from 'react';

export interface LogViewerProps {
  logText: string | null | undefined;
  className?: string;
}

// Always-dark terminal palette — uses the fixed `--log-*` token family only.
// Do not mix in the main app palette tokens here.
export function LogViewer({ logText, className = '' }: LogViewerProps) {
  const viewerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const viewer = viewerRef.current;
    if (viewer) viewer.scrollTop = viewer.scrollHeight;
  }, [logText]);

  return (
    <div
      ref={viewerRef}
      role="region"
      aria-label="Sync log"
      className={`max-h-96 overflow-auto rounded-md border border-log-border bg-log-bg p-3 font-mono text-xs ${className}`}
    >
      {logText ? (
        <pre className="whitespace-pre-wrap break-words text-log-text">{logText}</pre>
      ) : (
        <p className="text-log-text-muted">No log output yet.</p>
      )}
    </div>
  );
}
