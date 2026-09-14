import type { Metadata } from 'next';
import { DM_Sans, IBM_Plex_Mono } from 'next/font/google';
import { NavSidebar } from '@/components/NavSidebar';
import { HoursFormatProvider } from '@/lib/HoursFormatContext';
import { ThemeProvider } from '@/lib/ThemeContext';
import { THEME_STORAGE_KEY } from '@/lib/theme/constants';
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

const themeInitializationScript = `
  (() => {
    try {
      const stored = window.localStorage.getItem('${THEME_STORAGE_KEY}');
      const theme = stored === 'light' || stored === 'dark'
        ? stored
        : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    } catch (_) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${dmSans.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitializationScript }} />
      </head>
      <body className="antialiased">
        <ThemeProvider>
          <HoursFormatProvider>
            <div className="flex min-h-screen">
              <NavSidebar />
              <main className="min-w-0 flex-1 overflow-auto">{children}</main>
            </div>
          </HoursFormatProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
