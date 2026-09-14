import type { Metadata } from 'next';
import { DM_Sans, IBM_Plex_Mono } from 'next/font/google';
import { NavSidebar } from '@/components/NavSidebar';
import { HoursFormatProvider } from '@/lib/HoursFormatContext';
import './globals.css';

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Jira Timesheets',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${dmSans.variable} ${ibmPlexMono.variable}`}>
      <body>
        <HoursFormatProvider>
          <div className="flex min-h-screen">
            <NavSidebar />
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </HoursFormatProvider>
      </body>
    </html>
  );
}
