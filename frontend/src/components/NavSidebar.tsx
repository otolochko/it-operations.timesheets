'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/', label: 'Timesheets' },
  { href: '/sync', label: 'Sync Settings' },
];

export function NavSidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex h-full w-56 flex-col gap-1 border-r border-border bg-surface-raised p-3">
      {links.map((link) => {
        const isActive = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md border-l-2 px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? 'border-accent bg-card text-accent'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
