'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ThemeToggle } from '@/components/ThemeToggle';

interface IconProps {
  className?: string;
}

function TimesheetIcon({ className = '' }: IconProps) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={className}>
      <rect
        x="3.5"
        y="4.5"
        width="17"
        height="16"
        rx="2.5"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M8 2.8v3.4M16 2.8v3.4M3.5 9h17M8 13h3M8 17h6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SyncIcon({ className = '' }: IconProps) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M19.5 8A8 8 0 0 0 5.7 5.7L3.5 8M4.5 16a8 8 0 0 0 13.8 2.3l2.2-2.3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M3.5 3.8V8h4.2M20.5 20.2V16h-4.2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const links = [
  { href: '/', label: 'Timesheets', icon: TimesheetIcon },
  { href: '/sync', label: 'Sync settings', icon: SyncIcon },
];

export function NavSidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 flex h-screen w-20 shrink-0 flex-col border-r border-border bg-sidebar px-3 py-4 md:w-64 md:px-4 md:py-5">
      <div className="flex min-h-11 items-center justify-center gap-3 px-1 md:justify-start">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-sm font-bold tracking-tight text-white shadow-accent">
          JT
        </span>
        <div className="hidden min-w-0 md:block">
          <p className="truncate text-sm font-semibold text-text-primary">Timesheets</p>
          <p className="truncate text-xs text-text-muted">Jira operations</p>
        </div>
      </div>

      <div className="my-5 h-px bg-border" />

      <nav aria-label="Main navigation" className="flex flex-col gap-1.5">
        {links.map((link) => {
          const isActive = pathname === link.href;
          const Icon = link.icon;

          return (
            <Link
              key={link.href}
              href={link.href}
              title={link.label}
              aria-current={isActive ? 'page' : undefined}
              className={`group flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent md:justify-start ${
                isActive
                  ? 'bg-accent-soft text-accent'
                  : 'text-text-muted hover:bg-sidebar-hover hover:text-text-primary'
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="hidden md:block">{link.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-border pt-4">
        <ThemeToggle />
      </div>
    </aside>
  );
}
